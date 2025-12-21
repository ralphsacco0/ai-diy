document.addEventListener('DOMContentLoaded', async () => {
  try {
    const response = await fetch('/api/user', { credentials: 'include' });
    const data = await response.json();

    if (!data.success) {
      window.location.href = '/login';
      return;
    }

    document.getElementById('welcome').textContent = `Welcome, ${data.data.name}`;

    const role = data.data.role;
    const links = role === 'hr' ? [
      { text: 'Employee Directory', href: '/employee-directory' },
      { text: 'Leave Approvals', href: '/leave-approvals' },
      { text: 'Documents', href: '/documents' }
    ] : [
      { text: 'My Leave Requests', href: '/my-leaves' },
      { text: 'Update Profile', href: '/update-profile' }
    ];

    document.getElementById('nav-links').innerHTML = links.map(l => 
      `<li class='hover:bg-blue-100 p-2 rounded'><a href='${l.href}' aria-label='${l.text}'>${l.text}</a></li>`
    ).join('');
  } catch (err) {
    console.error(err);
  }

  // Sidebar toggle for responsive navigation
  const toggleBtn = document.getElementById('toggle-sidebar');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const mainContent = document.querySelector('.flex-1');

  if (toggleBtn) {
    const toggleSidebar = () => {
      const isOpen = sidebar.classList.contains('translate-x-0');
      if (isOpen) {
        sidebar.classList.remove('translate-x-0');
        overlay.classList.add('hidden');
        mainContent.classList.remove('ml-72');
      } else {
        sidebar.classList.add('translate-x-0');
        overlay.classList.remove('hidden');
        mainContent.classList.add('ml-72');
      }
    };

    toggleBtn.addEventListener('click', toggleSidebar);

    if (overlay) {
      overlay.addEventListener('click', () => {
        if (sidebar.classList.contains('translate-x-0')) {
          toggleSidebar();
        }
      });
    }
  }
});