// Onboarding JavaScript for US-005

// Common initialization: Fetch current user
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('user', { credentials: 'same-origin' });
        if (!response.ok) {
            window.location.href = 'login';
            return;
        }
        const user = await response.json();
        document.getElementById('user-name').textContent = user.name || user.email;
        window.currentUser = user; // Store globally for access
    } catch (err) {
        console.error('Failed to load user:', err);
        window.location.href = 'login';
    }

    // Check if on onboarding page
    if (document.querySelector('.onboarding-page') || window.location.pathname.includes('onboarding')) {
        initOnboardingPage();
    }
});

function initOnboardingPage() {
    const path = window.location.pathname;
    const pathParts = path.split('/');
    const employeeId = pathParts[pathParts.length - 1];

    if (path.endsWith('onboarding-assign.html')) {
        initAssignPage();
    } else if (path.endsWith('onboarding-pending.html')) {
        initPendingPage();
    } else if (path.includes('onboarding/') && employeeId && !isNaN(employeeId)) {
        initChecklistPage(employeeId);
    }
}

// Assign page: onboarding-assign.html
async function initAssignPage() {
    try {
        // Fetch employees for select
        const resp = await fetch('api/employees', { credentials: 'same-origin' });
        if (!resp.ok) throw new Error('Failed to load employees');
        const employees = await resp.json();
        const select = document.getElementById('employee-select');
        employees.employees.forEach(emp => {
            const option = document.createElement('option');
            option.value = emp.id;
            option.textContent = `${emp.name} (${emp.email})`;
            select.appendChild(option);
        });

        // Add task functionality
        document.getElementById('add-task-btn').addEventListener('click', addTaskInput);

        // Form submit
        document.getElementById('assign-form').addEventListener('submit', handleAssignSubmit);
    } catch (err) {
        showError('Failed to initialize assign page: ' + err.message);
    }
}

function addTaskInput() {
    const container = document.getElementById('tasks-container');
    const taskIndex = container.children.length;
    const div = document.createElement('div');
    div.className = 'flex space-x-2 mb-2';
    div.innerHTML = `
        <input type="text" placeholder="Task name" class="flex-1 p-2 border border-gray-300 rounded-md" name="task-name-${taskIndex}">
        <select class="p-2 border border-gray-300 rounded-md" name="task-type-${taskIndex}">
            <option value="checkbox">Checkbox</option>
            <option value="upload">Upload</option>
        </select>
        <button type="button" class="bg-red-500 text-white px-2 py-1 rounded" onclick="this.parentElement.remove()">Remove</button>
    `;
    container.appendChild(div);
}

async function handleAssignSubmit(e) {
    e.preventDefault();
    const employeeId = document.getElementById('employee-select').value;
    const startDate = document.getElementById('start-date').value;
    const tasksContainer = document.getElementById('tasks-container');
    const tasks = [];
    for (let i = 0; i < tasksContainer.children.length; i++) {
        const nameInput = tasksContainer.querySelector(`[name="task-name-${i}"]`);
        const typeSelect = tasksContainer.querySelector(`[name="task-type-${i}"]`);
        if (nameInput && nameInput.value.trim()) {
            tasks.push({
                name: nameInput.value.trim(),
                type: typeSelect.value
            });
        }
    }

    if (!employeeId || !startDate || tasks.length === 0) {
        showError('Please fill all required fields and add at least one task');
        return;
    }

    try {
        const response = await fetch('api/onboarding/assign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ employee_id: employeeId, start_date: startDate, tasks })
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to assign');
        }
        alert('Checklist assigned successfully');
        window.location.href = 'onboarding/pending';
    } catch (err) {
        showError('Error assigning checklist: ' + err.message);
    }
}

// Pending page: onboarding-pending.html
async function initPendingPage() {
    try {
        const response = await fetch('api/onboarding/pending', { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Failed to load pending checklists');
        const checklists = await response.json();
        const tbody = document.querySelector('#pending-table tbody');
        const noResults = document.getElementById('no-results');
        if (checklists.length === 0) {
            noResults.classList.remove('hidden');
            return;
        }
        noResults.classList.add('hidden');
        checklists.forEach(checklist => {
            const tr = document.createElement('tr');
            const progress = Math.round((JSON.parse(checklist.tasks).filter(t => t.completed).length / JSON.parse(checklist.tasks).length) * 100);
            tr.innerHTML = `
                <td class="px-4 py-2">${checklist.employee_name || 'Unknown'}</td>
                <td class="px-4 py-2">${checklist.start_date}</td>
                <td class="px-4 py-2">${progress}%</td>
                <td class="px-4 py-2"><a href="onboarding/${checklist.employee_id}" class="text-primary hover:underline">View</a></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        showError('Failed to load pending checklists: ' + err.message);
    }
}

// Checklist page: onboarding.html
async function initChecklistPage(employeeId) {
    try {
        const response = await fetch(`api/onboarding/${employeeId}`, { credentials: 'same-origin' });
        if (!response.ok) {
            const err = await response.json();
            if (response.status === 403) {
                alert('Unauthorized access to this checklist');
                window.location.href = 'dashboard';
                return;
            }
            throw new Error(err.error || 'Failed to load checklist');
        }
        const checklist = await response.json();
        const tasks = checklist.tasks || [];
        const taskList = document.getElementById('task-list');
        const progressSection = document.getElementById('progress-section');
        const noChecklist = document.getElementById('no-checklist');

        if (tasks.length === 0) {
            noChecklist.classList.remove('hidden');
            return;
        }
        noChecklist.classList.add('hidden');
        progressSection.classList.remove('hidden');

        tasks.forEach((task, index) => {
            const li = document.createElement('li');
            li.className = 'flex items-center space-x-3 p-3 bg-gray-50 rounded-md';
            let inputHtml;
            if (task.type === 'checkbox') {
                inputHtml = `<input type="checkbox" id="task-checkbox-${index}" ${task.completed ? 'checked' : ''} onchange="updateTask(${checklist.id}, ${index}, 'checkbox')">`;
            } else if (task.type === 'upload') {
                inputHtml = `<input type="file" id="task-upload-${index}" accept=".pdf,.docx" onchange="updateTask(${checklist.id}, ${index}, 'upload', this.files[0])" ${task.completed ? 'disabled' : ''}>`;
            }
            li.innerHTML = `
                <span>${task.name}</span>
                ${inputHtml}
                ${task.completed ? '<span class="ml-2 text-green-600">✓ Completed</span>' : ''}
            `;
            taskList.appendChild(li);
        });

        // Show save progress button for employee
        if (window.currentUser.role === 'employee') {
            document.getElementById('employee-view').classList.remove('hidden');
            document.getElementById('save-progress').addEventListener('click', () => updateProgress(checklist.id));
        }

        updateProgressBar(checklist.id);
    } catch (err) {
        showError('Failed to load checklist: ' + err.message);
    }
}

async function updateTask(checklistId, taskIndex, type, file = null) {
    try {
        let response;
        if (type === 'upload' && file) {
            const formData = new FormData();
            formData.append('completed', 'true');
            formData.append('file', file);
            response = await fetch(`api/onboarding/${checklistId}/task/${taskIndex}`, {
                method: 'PATCH',
                body: formData,
                credentials: 'same-origin'
            });
        } else {
            response = await fetch(`api/onboarding/${checklistId}/task/${taskIndex}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ completed: true })
            });
        }
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to update task');
        }
        // Refetch to update progress
        updateProgressBar(checklistId);
    } catch (err) {
        showError('Failed to update task: ' + err.message);
        // Revert UI if needed
        if (type === 'checkbox') {
            document.getElementById(`task-checkbox-${taskIndex}`).checked = false;
        }
    }
}

async function updateProgressBar(checklistId) {
    try {
        const response = await fetch(`api/onboarding/${checklistId}`, { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Failed to refetch');
        const checklist = await response.json();
        const tasks = checklist.tasks || [];
        const completedCount = tasks.filter(t => t.completed).length;
        const total = tasks.length;
        const percent = total > 0 ? Math.round((completedCount / total) * 100) : 0;
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        progressBar.style.width = percent + '%';
        progressText.textContent = percent + '% Complete';

        // Update task UI
        tasks.forEach((task, index) => {
            const checkbox = document.getElementById(`task-checkbox-${index}`);
            const upload = document.getElementById(`task-upload-${index}`);
            const li = document.querySelectorAll('#task-list li')[index];
            if (task.completed) {
                if (checkbox) checkbox.checked = true;
                if (upload) upload.disabled = true;
                if (li && !li.querySelector('.completed-span')) {
                    const span = document.createElement('span');
                    span.className = 'ml-2 text-green-600';
                    span.textContent = '✓ Completed';
                    li.appendChild(span);
                }
            }
        });
    } catch (err) {
        console.error('Failed to update progress:', err);
    }
}

function showError(message) {
    const errorEl = document.getElementById('error-message');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    } else {
        alert(message);
    }
}

// For saving overall progress (if needed, but per-task updates should suffice)
async function updateProgress(checklistId) {
    // This could refetch or mark all, but since tasks are individual, perhaps just refetch
    await updateProgressBar(checklistId);
    alert('Progress saved');
}