let user;

async function init() {
  const resp = await fetch('api/auth/user');
  if (!resp.ok) {
    window.location.href = 'login';
    return;
  }
  const fetchedUser = await resp.json();
  user = fetchedUser;
  document.getElementById('user-name').textContent = user.name || user.email;

  const uploadSection = document.getElementById('upload-section');
  if (user.role === 'employee') {
    uploadSection.style.display = 'block';
    document.getElementById('share').disabled = true;
  } else if (user.role === 'hr' || user.role === 'admin') {
    uploadSection.style.display = 'block';
    const exportBtn = document.createElement('button');
    exportBtn.textContent = 'Export All';
    exportBtn.className = 'bg-primary text-white px-4 py-2 rounded hover:bg-secondary ml-4';
    exportBtn.onclick = downloadExport;
    document.querySelector('h1').appendChild(exportBtn);
  } else {
    uploadSection.style.display = 'none';
  }
  loadDocuments(user);
}

async function loadDocuments(currentUser) {
  try {
    const resp = await fetch('api/documents/my');
    const docs = await resp.json();
    const tbody = document.getElementById('docs-table-body');
    tbody.innerHTML = docs.length ? '' : '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No documents found</td></tr>';
    docs.forEach(doc => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="px-6 py-4">${doc.original_name}</td>
        <td class="px-6 py-4">${doc.type}</td>
        <td class="px-6 py-4">${doc.upload_date}</td>
        <td class="px-6 py-4">
          <a href="api/documents/${doc.id}/download" class="text-primary mr-4">Download</a>
          ${(currentUser.role === 'hr' || currentUser.role === 'admin') ? `<button onclick="deleteDoc(${doc.id})" class="text-red-600">Delete</button>` : ''}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

document.getElementById('upload-form').addEventListener('submit', async e => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const resp = await fetch('api/documents/upload', {
    method: 'POST',
    body: formData
  });
  if (resp.ok) {
    e.target.reset();
    loadDocuments(user);
  } else {
    const err = await resp.json();
    alert(err.error || 'Upload failed');
  }
});

async function deleteDoc(id) {
  if (!confirm('Delete this document?')) return;
  const resp = await fetch(`api/documents/${id}`, {
    method: 'DELETE'
  });
  if (resp.ok) {
    loadDocuments(user);
  } else {
    alert('Delete failed');
  }
}

async function downloadExport() {
  const resp = await fetch('api/documents/export');
  if (resp.ok) {
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'documents.zip';
    a.click();
    URL.revokeObjectURL(url);
  } else {
    alert('Export failed');
  }
}

document.getElementById('logout-btn').addEventListener('click', async (e) => {
  e.preventDefault();
  await fetch('api/auth/logout', {
    method: 'POST'
  });
  window.location.href = 'login';
});

// Mobile toggle
const toggle = document.getElementById('mobile-toggle');
const sidebar = document.querySelector('nav');
if (toggle && sidebar) {
  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('hidden');
  });
}

init();