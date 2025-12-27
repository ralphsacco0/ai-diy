document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Fetch current user to check role
        const userResponse = await fetch('user');
        if (!userResponse.ok) {
            window.location.href = 'login';
            return;
        }
        const currentUser = await userResponse.json();

        // Check if HR or admin
        if (currentUser.role !== 'hr' && currentUser.role !== 'admin') {
            alert('Unauthorized access to pending reviews');
            window.location.href = 'dashboard';
            return;
        }

        // Fetch pending reviews
        const response = await fetch('api/reviews/pending');
        if (!response.ok) {
            if (response.status === 403) {
                alert('Unauthorized access');
                window.location.href = 'dashboard';
            } else {
                throw new Error('Failed to load pending reviews');
            }
            return;
        }
        const reviews = await response.json();

        // Populate table
        const tbody = document.querySelector('#pending-table tbody');
        if (tbody) {
            tbody.innerHTML = '';
            if (reviews.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" class="px-4 py-2 text-center text-gray-500">No pending reviews found</td></tr>';
            } else {
                for (const review of reviews) {
                    // Fetch employee name
                    const empResponse = await fetch(`api/employees/${review.employee_id}`);
                    if (!empResponse.ok) {
                        console.error('Failed to fetch employee:', review.employee_id);
                        continue;
                    }
                    const employee = await empResponse.json();
                    const name = employee.name;

                    const tr = document.createElement('tr');
                    tr.className = 'divide-y divide-gray-200';
                    tr.innerHTML = `
                        <td class="px-4 py-2">${name}</td>
                        <td class="px-4 py-2">${review.next_review_date || 'N/A'}</td>
                        <td class="px-4 py-2">
                            <a href="reviews/${review.employee_id}" class="bg-primary text-white px-3 py-1 rounded hover:bg-secondary">View</a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                }
            }
        }

        // Update user name in header
        const userNameEl = document.getElementById('user-name');
        if (userNameEl) {
            userNameEl.textContent = currentUser.name || currentUser.email;
        }

        // Mobile toggle
        const toggle = document.getElementById('mobile-toggle');
        const sidebar = document.querySelector('nav');
        if (toggle && sidebar) {
            toggle.addEventListener('click', () => {
                sidebar.classList.toggle('hidden');
            });
        }

        // Logout handler
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                fetch('api/auth/logout', { method: 'POST' }).then(() => {
                    window.location.href = 'login';
                });
            });
        }

    } catch (error) {
        console.error('Error loading pending reviews:', error);
        alert('Error: ' + error.message);
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.textContent = 'Error loading pending reviews: ' + error.message;
            errorEl.classList.remove('hidden');
        }
    }
});