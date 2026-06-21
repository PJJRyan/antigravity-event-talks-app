#!/usr/bin/env python3
import os
import sys
import json
import webbrowser
import threading
import socket
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# Global State
SELECTED_DIR = os.getcwd().replace('\\', '/')

def pick_directory():
    """
    Opens a native folder dialog to select a directory.
    Uses tkinter (which is standard and zero-dependency).
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askdirectory(title="Select Directory to Explore")
        root.destroy()
        if selected:
            return selected.replace('\\', '/')
    except Exception as e:
        print("GUI Selection failed: ", e)
    return None

def get_file_tree(root_dir):
    """
    Recursively scans the directory, structuring folders and files.
    Ignores common project environments and hidden files.
    """
    ignore_dirs = {'.git', 'venv', '.venv', 'env', '__pycache__', '.idea', '.vscode'}
    
    def walk_dir(path):
        tree = []
        try:
            for entry in os.scandir(path):
                if entry.name.startswith('.') or entry.name in ignore_dirs:
                    continue
                    
                rel_path = os.path.relpath(entry.path, root_dir).replace('\\', '/')
                abs_path = entry.path.replace('\\', '/')
                
                if entry.is_dir():
                    tree.append({
                        "name": entry.name,
                        "path": rel_path,
                        "absPath": abs_path,
                        "type": "directory",
                        "children": walk_dir(entry.path)
                    })
                else:
                    tree.append({
                        "name": entry.name,
                        "path": rel_path,
                        "absPath": abs_path,
                        "type": "file"
                    })
        except Exception as e:
            pass
        
        # Sort directories first, then files alphabetically
        tree.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        return tree
        
    return walk_dir(root_dir)

class ExplorerHTTPHandler(SimpleHTTPRequestHandler):
    """
    HTTP Server Handler serving the HTML UI and JSON API.
    """
    def log_message(self, format, *args):
        # Suppress logging to keep CLI clean
        return

    def do_GET(self):
        global SELECTED_DIR
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.replace('__INITIAL_DIR__', SELECTED_DIR).encode('utf-8'))
        elif self.path == '/api/files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                tree = get_file_tree(SELECTED_DIR)
                res = json.dumps({"status": "success", "dir": SELECTED_DIR, "data": tree})
            except Exception as e:
                res = json.dumps({"status": "error", "message": str(e)})
            self.wfile.write(res.encode('utf-8'))
        elif self.path == '/api/select_dir':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            new_dir = pick_directory()
            if new_dir:
                SELECTED_DIR = new_dir
                res = json.dumps({"status": "success", "dir": SELECTED_DIR})
            else:
                res = json.dumps({"status": "cancelled", "dir": SELECTED_DIR})
            self.wfile.write(res.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def find_free_port():
    """Finds an unused port on localhost."""
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

# Standalone UI Template
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Interactive File Tree Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-secondary: #121824;
      --bg-tertiary: #1e2538;
      --border-color: #2b364e;
      --accent-cyan: #06b6d4;
      --accent-cyan-hover: #0891b2;
      --accent-green: #10b981;
      --text-primary: #f3f4f6;
      --text-secondary: #9ca3af;
      --text-muted: #6b7280;
      --border-radius: 12px;
      --transition: 0.15s ease;
    }

    :root.light-mode {
      --bg-primary: #f8fafc;
      --bg-secondary: #ffffff;
      --bg-tertiary: #f1f5f9;
      --border-color: #cbd5e1;
      --accent-cyan: #0891b2;
      --accent-cyan-hover: #0369a1;
      --accent-green: #059669;
      --text-primary: #0f172a;
      --text-secondary: #334155;
      --text-muted: #64748b;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: 'Inter', sans-serif;
      line-height: 1.5;
      padding: 2.5rem 1.5rem;
      transition: background-color var(--transition), color var(--transition);
    }

    .container {
      max-width: 900px;
      margin: 0 auto;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border-color);
    }

    h1 {
      font-size: 1.5rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    h1 span {
      background: linear-gradient(135deg, var(--accent-cyan) 0%, #a855f7 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 600;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all var(--transition);
      color: var(--text-primary);
      background-color: var(--bg-secondary);
      border-color: var(--border-color);
    }

    .btn:hover {
      background-color: var(--bg-tertiary);
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--accent-cyan) 0%, #0284c7 100%);
      color: white;
      border: none;
      box-shadow: 0 4px 10px rgba(6, 182, 212, 0.15);
    }

    .btn-primary:hover {
      filter: brightness(1.1);
      transform: translateY(-1px);
    }

    .btn-icon {
      padding: 0.6rem;
      aspect-ratio: 1/1;
      justify-content: center;
    }

    .current-dir-banner {
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius);
      padding: 1.25rem;
      margin-bottom: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
    }

    .dir-info {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      overflow: hidden;
    }

    .dir-label {
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.05em;
    }

    .dir-path {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.95rem;
      color: var(--accent-cyan);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Controls Panel */
    .controls-panel {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    @media (max-width: 600px) {
      .controls-panel {
        grid-template-columns: 1fr;
      }
    }

    .search-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }

    .search-input {
      width: 100%;
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      border-radius: 8px;
      padding: 0.625rem 1rem 0.625rem 2.25rem;
      font-size: 0.9rem;
      transition: border-color var(--transition);
    }

    .search-input:focus {
      outline: none;
      border-color: var(--accent-cyan);
    }

    .search-icon {
      position: absolute;
      left: 0.8rem;
      color: var(--text-secondary);
    }

    .options-wrapper {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    /* Toggle Switch */
    .toggle-container {
      display: flex;
      align-items: center;
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.3rem;
      gap: 0.2rem;
    }

    .toggle-btn {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all var(--transition);
    }

    .toggle-btn.active {
      background-color: var(--accent-cyan);
      color: white;
    }

    /* File Tree Section */
    .tree-container {
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius);
      padding: 1.5rem 1rem;
      min-height: 450px;
      max-height: 65vh;
      overflow-y: auto;
    }

    .tree-node {
      display: flex;
      flex-direction: column;
      margin-left: 1.25rem;
    }

    .tree-node-root {
      margin-left: 0;
    }

    .tree-row {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.5rem;
      border-radius: 6px;
      cursor: pointer;
      transition: background var(--transition);
      user-select: none;
    }

    .tree-row:hover {
      background-color: var(--bg-tertiary);
    }

    .folder-arrow {
      width: 14px;
      height: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary);
      transition: transform var(--transition);
      cursor: pointer;
    }

    .tree-row.collapsed .folder-arrow {
      transform: rotate(-90deg);
    }

    .node-icon {
      width: 16px;
      height: 16px;
      color: var(--accent-cyan);
      flex-shrink: 0;
    }

    .node-icon.file {
      color: var(--text-secondary);
    }

    .node-name {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      flex-grow: 1;
      word-break: break-all;
    }

    .copy-badge {
      font-size: 0.65rem;
      background-color: rgba(6, 182, 212, 0.1);
      color: var(--accent-cyan);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      border: 1px solid rgba(6, 182, 212, 0.2);
      opacity: 0;
      transition: opacity var(--transition);
      flex-shrink: 0;
    }

    .tree-row:hover .copy-badge {
      opacity: 1;
    }

    .tree-children {
      display: flex;
      flex-direction: column;
    }

    .tree-row.collapsed + .tree-children {
      display: none;
    }

    .hidden-node {
      display: none !important;
    }

    /* Toast Notification */
    .toast-container {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 1000;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .toast {
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-left: 4px solid var(--accent-green);
      color: var(--text-primary);
      padding: 1rem 1.25rem;
      border-radius: 8px;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-width: 300px;
      max-width: 450px;
      transform: translateY(1rem);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .toast.visible {
      transform: translateY(0);
      opacity: 1;
    }

    .toast button {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      font-size: 1.1rem;
      margin-left: 1rem;
    }
  </style>
</head>
<body>

  <div class="container">
    <header>
      <h1>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-cyan);">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>File Tree Explorer</span>
      </h1>
      <div class="header-actions">
        <!-- Theme Toggle -->
        <button id="theme-btn" class="btn btn-icon" title="Toggle Theme">
          <svg class="theme-icon sun-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        </button>
      </div>
    </header>

    <div class="current-dir-banner">
      <div class="dir-info">
        <span class="dir-label">Exploring Directory</span>
        <span class="dir-path" id="dir-display">__INITIAL_DIR__</span>
      </div>
      <button id="change-dir-btn" class="btn btn-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 10l5 5-5 5M4 4h7a4 4 0 0 1 4 4v12"></path>
        </svg>
        <span>Change Folder</span>
      </button>
    </div>

    <div class="controls-panel">
      <!-- Search -->
      <div class="search-wrapper">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" id="search-input" class="search-input" placeholder="Search files and folders...">
      </div>
      <!-- Mode & Utility toggles -->
      <div class="options-wrapper">
        <button id="expand-all-btn" class="btn" title="Expand All Folders">Expand All</button>
        <button id="collapse-all-btn" class="btn" title="Collapse All Folders">Collapse All</button>
        <div class="toggle-container">
          <button id="mode-rel-btn" class="toggle-btn active">Relative Path</button>
          <button id="mode-abs-btn" class="toggle-btn">Absolute Path</button>
        </div>
      </div>
    </div>

    <!-- Tree View -->
    <div class="tree-container" id="tree-container">
      <div style="color:var(--text-secondary);text-align:center;padding:3rem;">Loading directory structure...</div>
    </div>
  </div>

  <div class="toast-container" id="toast-container"></div>

  <script>
    let currentTree = [];
    let copyMode = 'relative'; // 'relative' or 'absolute'
    
    // DOM Cache
    const dirDisplay = document.getElementById('dir-display');
    const changeDirBtn = document.getElementById('change-dir-btn');
    const searchInput = document.getElementById('search-input');
    const expandAllBtn = document.getElementById('expand-all-btn');
    const collapseAllBtn = document.getElementById('collapse-all-btn');
    const modeRelBtn = document.getElementById('mode-rel-btn');
    const modeAbsBtn = document.getElementById('mode-abs-btn');
    const treeContainer = document.getElementById('tree-container');
    const toastContainer = document.getElementById('toast-container');
    const themeBtn = document.getElementById('theme-btn');

    // 1. Theme handler
    themeBtn.addEventListener('click', () => {
      const isLight = document.documentElement.classList.toggle('light-mode');
      localStorage.setItem('theme', isLight ? 'light' : 'dark');
    });
    if (localStorage.getItem('theme') === 'light') {
      document.documentElement.classList.add('light-mode');
    }

    // 2. Toast alerts
    function showToast(message) {
      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.innerHTML = `<span>${message}</span><button>&times;</button>`;
      
      toast.querySelector('button').addEventListener('click', () => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 300);
      });
      
      toastContainer.appendChild(toast);
      setTimeout(() => toast.classList.add('visible'), 10);
      setTimeout(() => {
        if (toast.parentNode) {
          toast.classList.remove('visible');
          setTimeout(() => toast.remove(), 300);
        }
      }, 3500);
    }

    // 3. Copy to Clipboard
    function copyText(text, successMsg) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg);
      }).catch(err => {
        console.error(err);
        showToast("Clipboard copy failed!");
      });
    }

    // 4. Mode toggle
    modeRelBtn.addEventListener('click', () => {
      copyMode = 'relative';
      modeRelBtn.classList.add('active');
      modeAbsBtn.classList.remove('active');
    });
    modeAbsBtn.addEventListener('click', () => {
      copyMode = 'absolute';
      modeAbsBtn.classList.add('active');
      modeRelBtn.classList.remove('active');
    });

    // 5. Expand & Collapse
    expandAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.tree-row').forEach(row => {
        row.classList.remove('collapsed');
      });
    });
    collapseAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.tree-row').forEach(row => {
        if (row.getAttribute('data-type') === 'directory') {
          row.classList.add('collapsed');
        }
      });
    });

    // 6. Micro-interaction animation
    function triggerBadgeSuccess(btn) {
      const originalText = btn.textContent;
      btn.textContent = "✓ Copied";
      btn.style.color = "var(--accent-green)";
      btn.style.borderColor = "rgba(16, 185, 129, 0.3)";
      btn.style.backgroundColor = "rgba(16, 185, 129, 0.1)";
      
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.color = "";
        btn.style.borderColor = "";
        btn.style.backgroundColor = "";
      }, 1200);
    }

    // 7. Tree Renderer
    function renderTree(tree) {
      treeContainer.innerHTML = '';
      
      function createNode(node) {
        const nodeEl = document.createElement('div');
        nodeEl.className = 'tree-node';
        
        const rowEl = document.createElement('div');
        rowEl.className = 'tree-row';
        rowEl.setAttribute('data-path', node.path);
        rowEl.setAttribute('data-abspath', node.absPath);
        rowEl.setAttribute('data-type', node.type);
        
        let arrowHTML = '<div class="folder-arrow"></div>';
        let iconHTML = '';
        
        if (node.type === 'directory') {
          arrowHTML = `
            <div class="folder-arrow">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
          `;
          iconHTML = `
            <svg class="node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
          `;
        } else {
          iconHTML = `
            <svg class="node-icon file" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          `;
        }
        
        rowEl.innerHTML = `
          ${arrowHTML}
          ${iconHTML}
          <span class="node-name">${node.name}</span>
          <span class="copy-badge">Copy Path</span>
        `;
        
        nodeEl.appendChild(rowEl);
        
        if (node.type === 'directory' && node.children) {
          const childrenEl = document.createElement('div');
          childrenEl.className = 'tree-children';
          node.children.forEach(child => {
            childrenEl.appendChild(createNode(child));
          });
          nodeEl.appendChild(childrenEl);
          
          // Collapse / Expand toggle
          const toggles = rowEl.querySelectorAll('.folder-arrow, .node-icon');
          toggles.forEach(el => {
            el.addEventListener('click', (e) => {
              e.stopPropagation();
              rowEl.classList.toggle('collapsed');
            });
          });
        }
        
        // Copy action click handler
        rowEl.addEventListener('click', (e) => {
          if (e.target.closest('.folder-arrow') || e.target.closest('.node-icon')) {
            return;
          }
          
          const relPath = rowEl.getAttribute('data-path');
          const absPath = rowEl.getAttribute('data-abspath');
          const finalPath = (copyMode === 'relative') ? relPath : absPath;
          
          copyText(finalPath, `Copied ${copyMode} path!`);
          triggerBadgeSuccess(rowEl.querySelector('.copy-badge'));
        });
        
        return nodeEl;
      }
      
      tree.forEach(node => {
        const root = createNode(node);
        root.classList.add('tree-node-root');
        treeContainer.appendChild(root);
      });
    }

    // 8. API fetching
    async function loadTreeData() {
      try {
        const response = await fetch('/api/files');
        const res = await response.json();
        if (res.status === 'success') {
          currentTree = res.data;
          dirDisplay.textContent = res.dir;
          renderTree(currentTree);
          filterTree(searchInput.value);
        } else {
          treeContainer.innerHTML = `<div style="color:var(--accent-red);text-align:center;padding:3rem;">Error: ${res.message}</div>`;
        }
      } catch (err) {
        treeContainer.innerHTML = `<div style="color:var(--accent-red);text-align:center;padding:3rem;">Failed to fetch directory tree.</div>`;
      }
    }

    // 9. Change Directory triggers
    changeDirBtn.addEventListener('click', async () => {
      try {
        const response = await fetch('/api/select_dir');
        const res = await response.json();
        if (res.status === 'success') {
          loadTreeData();
          showToast("Loaded new directory successfully!");
        } else if (res.status === 'cancelled') {
          showToast("Directory selection cancelled.");
        }
      } catch (e) {
        showToast("Error opening file selector.");
      }
    });

    // 10. Real-time Search filter
    function filterTree(query) {
      const term = query.toLowerCase().trim();
      const rows = document.querySelectorAll('.tree-row');
      
      if (!term) {
        rows.forEach(row => {
          row.classList.remove('hidden-node');
          const children = row.nextElementSibling;
          if (children && children.classList.contains('tree-children')) {
            children.classList.remove('hidden-node');
          }
        });
        return;
      }
      
      // Hide all first
      rows.forEach(row => {
        row.classList.add('hidden-node');
        const children = row.nextElementSibling;
        if (children && children.classList.contains('tree-children')) {
          children.classList.add('hidden-node');
        }
      });
      
      // Reveal matches and expand branches
      rows.forEach(row => {
        const name = row.querySelector('.node-name').textContent.toLowerCase();
        if (name.includes(term)) {
          row.classList.remove('hidden-node');
          
          let parentNode = row.parentElement;
          while (parentNode && parentNode.classList.contains('tree-node')) {
            const parentRow = parentNode.querySelector('.tree-row');
            if (parentRow) {
              parentRow.classList.remove('hidden-node');
              parentRow.classList.remove('collapsed');
              const parentChildren = parentRow.nextElementSibling;
              if (parentChildren) {
                parentChildren.classList.remove('hidden-node');
              }
            }
            parentNode = parentNode.parentElement.closest('.tree-node');
          }
          
          const children = row.nextElementSibling;
          if (children && children.classList.contains('tree-children')) {
            children.classList.remove('hidden-node');
            children.querySelectorAll('.tree-row').forEach(childRow => {
              childRow.classList.remove('hidden-node');
            });
          }
        }
      });
    }

    searchInput.addEventListener('input', () => {
      filterTree(searchInput.value);
    });

    // Init
    loadTreeData();
  </script>
</body>
</html>
"""

def main():
    global SELECTED_DIR
    print("--------------------------------------------------")
    print("  Workspace File Explorer Standalone Utility     ")
    print("--------------------------------------------------")
    print("Opening directory selection dialog...")
    
    # Open directory selection initially
    chosen = pick_directory()
    if not chosen:
        print("No directory selected. Exiting Explorer.")
        sys.exit(0)
        
    SELECTED_DIR = chosen
    print(f"Selected: {SELECTED_DIR}")
    
    # Start web server on a free port
    port = find_free_port()
    addr = f"http://127.0.0.1:{port}"
    
    print(f"Starting lightweight web server on {addr}...")
    
    # Launch browser automatically
    def open_browser():
        webbrowser.open(addr)
        
    threading.Timer(1.0, open_browser).start()
    
    # Start server
    try:
        with TCPServer(('127.0.0.1', port), ExplorerHTTPHandler) as httpd:
            print("Server is active. Press CTRL+C in this terminal window to stop.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server. Goodbye!")

if __name__ == '__main__':
    main()
