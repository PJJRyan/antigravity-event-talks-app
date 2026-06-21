// BigQuery Release Pulse Frontend Engine

document.addEventListener('DOMContentLoaded', () => {
  // State variables
  let allReleases = []; // Raw entries from backend
  let parsedUpdates = []; // Extracted individual updates
  let selectedUpdateIds = new Set();
  let currentFilter = 'all';
  let searchQuery = '';
  let lastCheckedTime = null;

  // DOM Elements
  const refreshBtn = document.getElementById('refresh-btn');
  const exportCsvBtn = document.getElementById('export-csv-btn');
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const sunIcon = themeToggleBtn.querySelector('.sun-icon');
  const moonIcon = themeToggleBtn.querySelector('.moon-icon');
  const cacheStatus = document.getElementById('cache-status');

  // Theme Toggle Engine Initialization
  const savedTheme = localStorage.getItem('theme') || 'dark';
  if (savedTheme === 'light') {
    document.documentElement.classList.add('light-mode');
    sunIcon.classList.add('hidden');
    moonIcon.classList.remove('hidden');
  }
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search');
  const filterChips = document.querySelectorAll('.chip');
  const timeline = document.getElementById('notes-timeline');
  const skeletonLoading = document.getElementById('skeleton-loading');
  const emptyState = document.getElementById('empty-state');
  const resetFiltersBtn = document.getElementById('reset-filters-btn');
  
  // Stats Elements
  const statTotalDays = document.getElementById('stat-total-days');
  const statFeatures = document.getElementById('stat-features');
  const statIssues = document.getElementById('stat-issues');
  const statLastChecked = document.getElementById('stat-last-checked');

  // Selection Bar Elements
  const selectionBar = document.getElementById('selection-bar');
  const selectedCount = document.getElementById('selected-count');
  const tweetSelectedBtn = document.getElementById('tweet-selected-btn');
  const copySelectedBtn = document.getElementById('copy-selected-btn');
  const clearSelectionBtn = document.getElementById('clear-selection-btn');

  // Modal Elements
  const tweetModal = document.getElementById('tweet-modal');
  const closeModalBtn = document.getElementById('close-modal');
  const modalCancelBtn = document.getElementById('modal-cancel-btn');
  const modalCopyBtn = document.getElementById('modal-copy-btn');
  const modalTweetBtn = document.getElementById('modal-tweet-btn');
  const tweetTextarea = document.getElementById('tweet-textarea');
  const tweetPreviewText = document.getElementById('tweet-preview-text');
  const charCount = document.getElementById('char-count');
  const charProgressRing = document.getElementById('char-progress');
  const tweetLenWarning = document.getElementById('tweet-len-warning');

  // Toast Container
  const toastContainer = document.getElementById('toast-container');

  // 1. FETCH & PROCESS DATA
  
  // Show/Hide loading skeleton
  function setLoading(isLoading) {
    if (isLoading) {
      refreshBtn.classList.add('loading');
      refreshBtn.disabled = true;
      skeletonLoading.classList.remove('hidden');
      timeline.classList.add('hidden');
      emptyState.classList.add('hidden');
      document.querySelector('.status-dot').classList.add('spinning');
    } else {
      refreshBtn.classList.remove('loading');
      refreshBtn.disabled = false;
      skeletonLoading.classList.add('hidden');
      timeline.classList.remove('hidden');
      document.querySelector('.status-dot').classList.remove('spinning');
    }
  }

  // Toast Notification helper
  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${message}</span>
      <button style="background:none;border:none;color:inherit;cursor:pointer;font-size:1.1rem;margin-left:1rem;">&times;</button>
    `;
    
    // Close button event
    toast.querySelector('button').addEventListener('click', () => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 300);
    });

    toastContainer.appendChild(toast);
    
    // Force reflow and show
    setTimeout(() => toast.classList.add('visible'), 10);

    // Auto dismiss after 4 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 300);
      }
    }, 4000);
  }

  // Format timestamp relative or local
  function formatTime(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Parse raw release HTML into individual updates
  function parseReleaseNotes(entries) {
    const updates = [];
    const parser = new DOMParser();

    entries.forEach((entry, entryIndex) => {
      const doc = parser.parseFromString(entry.content, 'text/html');
      const children = Array.from(doc.body.children);
      
      let currentCategory = 'General';
      let currentElements = [];
      let updateSubIndex = 0;

      const pushCurrentUpdate = () => {
        if (currentElements.length > 0) {
          const tempDiv = document.createElement('div');
          currentElements.forEach(el => tempDiv.appendChild(el.cloneNode(true)));
          
          // Get text content for search index and Tweeting
          const text = tempDiv.textContent.trim();
          const html = tempDiv.innerHTML;
          
          const uniqueId = `up-${entryIndex}-${updateSubIndex}`;
          updates.push({
            id: uniqueId,
            date: entry.title,
            originalLink: entry.link,
            rawCategory: currentCategory,
            category: normalizeCategory(currentCategory),
            htmlContent: html,
            textContent: text
          });
          
          updateSubIndex++;
          currentElements = [];
        }
      };

      if (children.length === 0) {
        // If content is just plain text, or empty
        updates.push({
          id: `up-${entryIndex}-0`,
          date: entry.title,
          originalLink: entry.link,
          rawCategory: 'General',
          category: 'General',
          htmlContent: entry.content || '<p>No content details.</p>',
          textContent: entry.content ? doc.body.textContent.trim() : 'No content details.'
        });
        return;
      }

      children.forEach(child => {
        const tagName = child.tagName.toUpperCase();
        if (tagName === 'H3' || tagName === 'H4' || tagName === 'H2') {
          // Push previous section before starting new one
          pushCurrentUpdate();
          currentCategory = child.textContent.trim();
        } else {
          currentElements.push(child);
        }
      });

      // Push final section
      pushCurrentUpdate();
    });

    return updates;
  }

  // Normalize categories for styling and filtering
  function normalizeCategory(raw) {
    const cat = raw.toLowerCase().trim();
    if (cat.includes('feature')) return 'Feature';
    if (cat.includes('announcement')) return 'Announcement';
    if (cat.includes('change') || cat.includes('update')) return 'Changed';
    if (cat.includes('issue') || cat.includes('fix') || cat.includes('bug')) return 'Issue';
    if (cat.includes('deprecation')) return 'Deprecation';
    return 'General';
  }

  // Load feed from backend
  async function loadFeed(force = false) {
    setLoading(true);
    
    try {
      const response = await fetch(`/api/releases?refresh=${force}`);
      if (!response.ok) {
        throw new Error(`Server returned code ${response.status}`);
      }
      
      const res = await response.json();
      if (res.status === 'success') {
        allReleases = res.data;
        parsedUpdates = parseReleaseNotes(allReleases);
        
        lastCheckedTime = Math.floor(Date.now() / 1000);
        cacheStatus.textContent = res.from_cache ? "Connected (Cached)" : "Live Connected";
        
        updateStats();
        renderTimeline();
        
        // Reset selection when reload occurs
        clearSelection();
        
        if (force) {
          showToast("Feed refreshed successfully!");
        }
      } else {
        throw new Error(res.message || "Unknown server error");
      }
    } catch (err) {
      console.error(err);
      showToast(`Failed to load updates: ${err.message}`, 'error');
      
      if (parsedUpdates.length === 0) {
        timeline.innerHTML = `
          <div class="empty-state">
            <h3>Failed to load feed</h3>
            <p>We could not fetch the release notes. Please check your internet connection or try again.</p>
            <button id="retry-btn" class="btn btn-secondary">Retry Loading</button>
          </div>
        `;
        document.getElementById('retry-btn').addEventListener('click', () => loadFeed(true));
      }
    } finally {
      setLoading(false);
    }
  }

  // Compute statistics dashboard
  function updateStats() {
    statTotalDays.textContent = allReleases.length;
    
    const featureCount = parsedUpdates.filter(u => u.category === 'Feature').length;
    statFeatures.textContent = featureCount;
    
    const issueCount = parsedUpdates.filter(u => u.category === 'Issue' || u.category === 'Deprecation').length;
    statIssues.textContent = issueCount;
    
    statLastChecked.textContent = formatTime(lastCheckedTime);
  }

  // 2. TIMELINE RENDERING
  
  // Get currently filtered updates
  function getFilteredUpdates() {
    return parsedUpdates.filter(update => {
      // Category filter
      if (currentFilter !== 'all') {
        if (currentFilter === 'Issue') {
          // Group Issue and Deprecation together for filters
          if (update.category !== 'Issue' && update.category !== 'Deprecation') return false;
        } else if (update.category !== currentFilter) {
          return false;
        }
      }
      
      // Search query filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const inText = update.textContent.toLowerCase().includes(query);
        const inDate = update.date.toLowerCase().includes(query);
        const inCategory = update.rawCategory.toLowerCase().includes(query);
        if (!inText && !inDate && !inCategory) return false;
      }
      
      return true;
    });
  }

  // Render timeline cards
  function renderTimeline() {
    // Filter updates
    let filtered = getFilteredUpdates();

    if (filtered.length === 0) {
      timeline.innerHTML = '';
      emptyState.classList.remove('hidden');
      return;
    }
    
    emptyState.classList.add('hidden');
    
    // Group filtered updates by Date
    const grouped = {};
    filtered.forEach(update => {
      if (!grouped[update.date]) {
        grouped[update.date] = [];
      }
      grouped[update.date].push(update);
    });

    // Generate HTML
    let html = '';
    
    Object.keys(grouped).forEach(date => {
      const updatesForDate = grouped[date];
      const link = updatesForDate[0].originalLink;
      
      html += `
        <div class="date-group" data-date="${date}">
          <div class="date-marker">
            <div class="date-node">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
            </div>
            <span class="date-title">${date}</span>
          </div>
          <div class="date-cards">
      `;

      updatesForDate.forEach(update => {
        const isSelected = selectedUpdateIds.has(update.id);
        const categoryClass = update.category.toLowerCase();
        
        html += `
          <div class="update-card ${isSelected ? 'selected' : ''}" data-id="${update.id}">
            <div class="select-checkbox-container">
              <div class="custom-checkbox"></div>
            </div>
            
            <div class="update-details">
              <div class="update-header-meta">
                <div class="update-badge-group">
                  <span class="tag-badge ${categoryClass}">${update.rawCategory}</span>
                </div>
                <div class="card-actions">
                  <button class="action-icon-btn btn-action-tweet" data-id="${update.id}" title="Tweet this update">
                    <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                  </button>
                  <button class="action-icon-btn btn-action-copy" data-id="${update.id}" title="Copy description to clipboard">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  </button>
                  <a href="${update.originalLink}" target="_blank" class="action-icon-btn" title="View official release log">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                  </a>
                </div>
              </div>
              <div class="update-description">
                ${update.htmlContent}
              </div>
            </div>
          </div>
        `;
      });

      html += `
          </div>
        </div>
      `;
    });

    timeline.innerHTML = html;
    attachCardListeners();
  }

  // Click handler helpers
  function attachCardListeners() {
    // Card item selection
    document.querySelectorAll('.update-card').forEach(card => {
      card.addEventListener('click', (e) => {
        // Prevent click trigger if they clicked an action button or link
        if (e.target.closest('.card-actions') || e.target.closest('a')) {
          return;
        }
        
        const updateId = card.getAttribute('data-id');
        toggleSelection(updateId);
      });
    });

    // Individual Action Button - Tweet
    document.querySelectorAll('.btn-action-tweet').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        const update = parsedUpdates.find(u => u.id === id);
        if (update) {
          openTweetModal([update]);
        }
      });
    });

    // Individual Action Button - Copy
    document.querySelectorAll('.btn-action-copy').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        const update = parsedUpdates.find(u => u.id === id);
        if (update) {
          copyUpdateToClipboard(update);
        }
      });
    });
  }

  // 3. SELECTION LOGIC
  
  // Toggle selection state for a specific update card
  function toggleSelection(id) {
    if (selectedUpdateIds.has(id)) {
      selectedUpdateIds.delete(id);
    } else {
      selectedUpdateIds.add(id);
    }
    
    // Update card class visually
    const card = document.querySelector(`.update-card[data-id="${id}"]`);
    if (card) {
      card.classList.toggle('selected');
    }
    
    updateSelectionBar();
  }

  // Clear all selections
  function clearSelection() {
    selectedUpdateIds.clear();
    document.querySelectorAll('.update-card.selected').forEach(c => {
      c.classList.remove('selected');
    });
    updateSelectionBar();
  }

  // Shows or hides the bottom action bar based on selected count
  function updateSelectionBar() {
    const count = selectedUpdateIds.size;
    selectedCount.textContent = count;
    
    if (count > 0) {
      selectionBar.classList.add('visible');
    } else {
      selectionBar.classList.remove('visible');
    }
  }

  // Helper to escape values for CSV format
  function escapeCSV(text) {
    if (text === null || text === undefined) return '';
    return '"' + text.toString().replace(/"/g, '""') + '"';
  }

  // Exports currently filtered updates to a CSV file
  function exportToCSV() {
    const filtered = getFilteredUpdates();
    if (filtered.length === 0) {
      showToast("No updates to export", "error");
      return;
    }

    const headers = ["Date", "Category", "Sub-Category", "Description", "Link"];
    const csvRows = [headers.map(escapeCSV).join(",")];

    filtered.forEach(u => {
      const row = [
        u.date,
        u.category,
        u.rawCategory,
        u.textContent,
        u.originalLink
      ];
      csvRows.push(row.map(escapeCSV).join(","));
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `bigquery_release_notes_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast(`Successfully exported ${filtered.length} updates to CSV!`);
  }

  // 4. SHARING & TWITTER LOGIC
  
  // Helper to copy text to clipboard
  function copyTextToClipboard(text, successMsg) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg || "Copied to clipboard!");
    }).catch(err => {
      console.error('Failed to copy text: ', err);
      showToast("Failed to copy text. Please copy manually.", "error");
    });
  }

  // Copy single update details to clipboard
  function copyUpdateToClipboard(update) {
    const cleanText = `BigQuery Update (${update.date}) - [${update.rawCategory}]: ${update.textContent}\nSource: ${update.originalLink}`;
    copyTextToClipboard(cleanText, "Update text copied to clipboard!");
  }

  // Character counter helper (X counts all links as 23 characters)
  function getXTweetLength(text) {
    // Regex for URLs
    const urlRegex = /https?:\/\/[^\s]+/g;
    let urlCount = 0;
    let cleanedText = text.replace(urlRegex, () => {
      urlCount++;
      return ""; // Temporarily strip URLs
    });
    
    // Total character count = length of stripped text + 23 chars per URL
    return cleanedText.length + (urlCount * 23);
  }

  // Generate pre-filled tweet from updates
  function generateTweetContent(updates) {
    if (updates.length === 1) {
      const update = updates[0];
      const categoryText = update.rawCategory.toUpperCase();
      const cleanDesc = update.textContent.substring(0, 160).trim();
      const dots = update.textContent.length > 160 ? '...' : '';
      
      return `BigQuery Update (${update.date}) | ${categoryText}\n\n"${cleanDesc}${dots}"\n\nRead more: ${update.originalLink}\n#BigQuery #GoogleCloud`;
    } else {
      // Multiple updates selected
      let tweet = `BigQuery Updates Summary (${updates[0].date}):\n`;
      updates.slice(0, 3).forEach(u => {
        tweet += `\n• [${u.rawCategory}] ${u.textContent.substring(0, 50)}...`;
      });
      
      if (updates.length > 3) {
        tweet += `\n• And ${updates.length - 3} more updates.`;
      }
      
      tweet += `\n\nFull release notes: ${updates[0].originalLink}\n#BigQuery #GoogleCloud`;
      return tweet;
    }
  }

  // Open Tweet Modal
  function openTweetModal(updates) {
    const defaultText = generateTweetContent(updates);
    tweetTextarea.value = defaultText;
    updateTweetStats(defaultText);
    
    tweetModal.classList.add('visible');
    tweetTextarea.focus();
  }

  // Update Modal Tweet stats & preview
  function updateTweetStats(text) {
    const len = getXTweetLength(text);
    charCount.textContent = len;
    
    // Progress Ring Calculation
    // Circumference is 62.83
    const maxLen = 280;
    const percentage = Math.min(len / maxLen, 1);
    const offset = 62.83 - (percentage * 62.83);
    charProgressRing.style.strokeDashoffset = offset;
    
    // Status Classes
    const wrapper = document.querySelector('.char-count-wrapper');
    wrapper.className = 'char-count-wrapper';
    
    if (len > 280) {
      wrapper.classList.add('danger');
      charProgressRing.style.stroke = 'var(--accent-red)';
      tweetLenWarning.classList.remove('hidden');
      modalTweetBtn.disabled = true;
    } else if (len > 250) {
      wrapper.classList.add('warning');
      charProgressRing.style.stroke = 'var(--accent-orange)';
      tweetLenWarning.classList.add('hidden');
      modalTweetBtn.disabled = false;
    } else {
      charProgressRing.style.stroke = 'var(--accent-cyan)';
      tweetLenWarning.classList.add('hidden');
      modalTweetBtn.disabled = false;
    }

    // Render Preview Box HTML (highlighting hashtags/links)
    let previewHTML = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/(#[a-zA-Z0-9_]+)/g, '<span class="preview-hashtag">$1</span>')
      .replace(/(https?:\/\/[^\s]+)/g, '<span class="preview-link">$1</span>');
      
    tweetPreviewText.innerHTML = previewHTML;
  }

  // Open external window to post on X
  function publishTweet(text) {
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank', 'width=550,height=420,menubar=no,toolbar=no,scrollbars=yes');
    showToast("Opening X sharing dialog...");
    tweetModal.classList.remove('visible');
  }

  // 5. EVENT LISTENERS
  
  // Refresh button click
  refreshBtn.addEventListener('click', () => loadFeed(true));

  // Export CSV button click
  exportCsvBtn.addEventListener('click', exportToCSV);

  // Theme Toggle button click
  themeToggleBtn.addEventListener('click', () => {
    const isLight = document.documentElement.classList.toggle('light-mode');
    if (isLight) {
      localStorage.setItem('theme', 'light');
      sunIcon.classList.add('hidden');
      moonIcon.classList.remove('hidden');
      showToast("Switched to Light Theme");
    } else {
      localStorage.setItem('theme', 'dark');
      moonIcon.classList.add('hidden');
      sunIcon.classList.remove('hidden');
      showToast("Switched to Dark Theme");
    }
  });

  // Search input typing
  searchInput.addEventListener('input', () => {
    searchQuery = searchInput.value;
    clearSearchBtn.style.display = searchQuery ? 'block' : 'none';
    renderTimeline();
  });

  // Clear search query
  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
    renderTimeline();
  });

  // Category chip filters
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentFilter = chip.getAttribute('data-filter');
      renderTimeline();
    });
  });

  // Reset all filters in empty state
  resetFiltersBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    
    filterChips.forEach(c => c.classList.remove('active'));
    document.querySelector('.chip[data-filter="all"]').classList.add('active');
    currentFilter = 'all';
    
    renderTimeline();
  });

  // Floating Bar: Clear selections
  clearSelectionBtn.addEventListener('click', clearSelection);

  // Floating Bar: Copy selected updates
  copySelectedBtn.addEventListener('click', () => {
    const selectedUpdates = parsedUpdates.filter(u => selectedUpdateIds.has(u.id));
    if (selectedUpdates.length === 0) return;
    
    let combinedText = `BigQuery Updates Summaries (Count: ${selectedUpdates.length}):\n`;
    selectedUpdates.forEach((u, i) => {
      combinedText += `\n[${i+1}] ${u.date} - [${u.rawCategory}]: ${u.textContent}\nSource: ${u.originalLink}\n`;
    });
    
    copyTextToClipboard(combinedText, `${selectedUpdates.length} updates copied to clipboard!`);
    clearSelection();
  });

  // Floating Bar: Tweet Selected modal open
  tweetSelectedBtn.addEventListener('click', () => {
    const selectedUpdates = parsedUpdates.filter(u => selectedUpdateIds.has(u.id));
    if (selectedUpdates.length === 0) return;
    openTweetModal(selectedUpdates);
  });

  // Modal Textarea Input
  tweetTextarea.addEventListener('input', () => {
    updateTweetStats(tweetTextarea.value);
  });

  // Modal Cancel & Close buttons
  const closeModal = () => tweetModal.classList.remove('visible');
  closeModalBtn.addEventListener('click', closeModal);
  modalCancelBtn.addEventListener('click', closeModal);
  
  // Close modal when clicking outside the card
  tweetModal.addEventListener('click', (e) => {
    if (e.target === tweetModal) {
      closeModal();
    }
  });

  // Modal Copy Button
  modalCopyBtn.addEventListener('click', () => {
    copyTextToClipboard(tweetTextarea.value, "Tweet text copied to clipboard!");
    closeModal();
  });

  // Modal Tweet/Share button
  modalTweetBtn.addEventListener('click', () => {
    if (getXTweetLength(tweetTextarea.value) <= 280) {
      publishTweet(tweetTextarea.value);
      clearSelection();
    }
  });

  // Initial Load on startup
  loadFeed(false);
});
