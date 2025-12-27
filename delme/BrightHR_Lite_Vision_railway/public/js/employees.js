if (document.getElementById('searchForm')) { // For employees.html
    const loadEmployees = async (search = '') => {
        try {
            let url = 'api/employees';
            if (search) {
                url += `?search=${encodeURIComponent(search)}`;
            }
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load');
            const data = await response.json();
            const tbody = document.getElementById('employeesTable').querySelector('tbody');
            tbody.innerHTML = '';
            const noResults = document.getElementById('noResults');
            if (noResults) noResults.classList.add('hidden');
            const errorMsg = document.getElementById('errorMsg');
            if (errorMsg) errorMsg.classList.add('hidden');
            if (data.employees.length === 0) {
                if (noResults) noResults.classList.remove('hidden');
            } else {
                data.employees.forEach(emp => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="px-4 py-2 border">${emp.name}</td>
                        <td class="px-4 py-2 border">${emp.email}</td>
                        <td class="px-4 py-2 border">${emp.phone || ''}</td>
                        <td class="px-4 py-2 border">${emp.department}</td>
                        <td class="px-4 py-2 border">${emp.hire_date}</td>
                        <td class="px-4 py-2 border"><a href="employees/edit/${emp.id}" class="text-blue-500 hover:underline">Edit</a></td>
                        <td class="px-4 py-2 border"><a href="reviews/${emp.id}" class="text-blue-500 hover:underline">Performance Reviews</a></td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (err) {
            alert('Error loading employees: ' + err.message);
        }
    };
    loadEmployees(); // Initial load
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const search = document.getElementById('searchInput').value;
            loadEmployees(search);
        });
    }
}

if (document.getElementById('addForm')) { // For add
    document.getElementById('addForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        try {
            const response = await fetch('api/employees', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to add');
            }
            window.location.href = 'employees';
        } catch (err) {
            alert('Error: ' + err.message);
        }
    });
}

if (document.getElementById('editForm')) { // For edit
    const pathParts = window.location.pathname.split('/');
    const id = pathParts[pathParts.length - 1];
    const populateForm = async () => {
        try {
            const response = await fetch(`api/employees/${id}`);
            if (!response.ok) throw new Error('Employee not found');
            const emp = await response.json();
            document.getElementById('name').value = emp.name || '';
            document.getElementById('email').value = emp.email || '';
            document.getElementById('phone').value = emp.phone || '';
            document.getElementById('department').value = emp.department || 'HR';
            document.getElementById('hire_date').value = emp.hire_date || '';
        } catch (err) {
            alert('Error loading employee: ' + err.message);
        }
    };
    populateForm();
    document.getElementById('editForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        try {
            const response = await fetch(`api/employees/${id}`, {
                method: 'PATCH',
                body: formData
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to update');
            }
            window.location.href = 'employees';
        } catch (err) {
            alert('Error: ' + err.message);
        }
    });
}