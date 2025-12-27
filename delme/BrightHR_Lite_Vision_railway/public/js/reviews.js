document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Fetch current user for role check
        const userResponse = await fetch('user');
        if (!userResponse.ok) {
            window.location.href = 'login';
            return;
        }
        const currentUser = await userResponse.json();
        window.currentUser = currentUser;

        // Hide create section if not HR or admin
        if (currentUser.role !== 'hr' && currentUser.role !== 'admin') {
            const createSection = document.getElementById('create-review-section');
            if (createSection) {
                createSection.style.display = 'none';
            }
        }

        // Parse employeeId from URL
        const pathParts = window.location.pathname.split('/');
        const employeeId = pathParts[2];
        if (!employeeId || isNaN(employeeId)) {
            throw new Error('Invalid employee ID');
        }

        // Fetch employee name
        const empResponse = await fetch(`api/employees/${employeeId}`);
        if (!empResponse.ok) {
            throw new Error('Failed to fetch employee');
        }
        const employee = await empResponse.json();
        document.getElementById('employee-name').textContent = `${employee.name} - Performance Reviews`;

        // Fetch and populate reviews
        await loadReviews(employeeId);

        // Set up create form if visible
        const createForm = document.getElementById('create-review-form');
        if (createForm) {
            createForm.addEventListener('submit', (e) => handleCreateReview(e, employeeId));
        }

    } catch (error) {
        console.error('Initialization error:', error);
        alert('Error loading page: ' + error.message);
    }
});

async function loadReviews(employeeId) {
    try {
        const response = await fetch(`api/reviews/${employeeId}`);
        if (!response.ok) {
            if (response.status === 403) {
                alert('Unauthorized access');
            } else {
                throw new Error('Failed to load reviews');
            }
            return;
        }
        const reviews = await response.json();

        const tbody = document.querySelector('#reviews-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        reviews.forEach(review => {
            const tr = document.createElement('tr');
            tr.className = 'divide-y divide-gray-200';
            tr.innerHTML = `
                <td class="px-4 py-2">${review.review_date}</td>
                <td class="px-4 py-2">${review.template_type}</td>
                <td class="px-4 py-2">
                    <span class="px-2 py-1 rounded text-sm ${getStatusClass(review.status)}">${review.status}</span>
                </td>
                <td class="px-4 py-2">
                    <button onclick="viewReview(${review.id}, ${employeeId})" class="bg-blue-500 text-white px-3 py-1 rounded mr-2 hover:bg-blue-600">View</button>
                    <button onclick="editReview(${review.id})" class="bg-green-500 text-white px-3 py-1 rounded hover:bg-green-600">Edit</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        console.error('Error loading reviews:', error);
        alert('Error: ' + error.message);
    }
}

function getStatusClass(status) {
    switch (status) {
        case 'draft': return 'bg-yellow-200 text-yellow-800';
        case 'assigned': return 'bg-blue-200 text-blue-800';
        case 'completed': return 'bg-green-200 text-green-800';
        default: return 'bg-gray-200 text-gray-800';
    }
}

async function handleCreateReview(e, employeeId) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        employee_id: employeeId,
        review_date: new Date().toISOString().split('T')[0],
        template_type: formData.get('template_type'),
        goals: formData.get('goals') ? JSON.parse(formData.get('goals')) : [],
        feedback: formData.get('feedback'),
        next_review_date: formData.get('next_review_date')
    };

    try {
        const response = await fetch('api/reviews/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            if (response.status === 403) {
                alert('Unauthorized to create review');
            } else {
                const err = await response.json();
                throw new Error(err.error || 'Failed to create review');
            }
            return;
        }
        e.target.reset();
        await loadReviews(employeeId);
        alert('Review created successfully');
    } catch (error) {
        console.error('Create error:', error);
        alert('Error: ' + error.message);
    }
}

// View Review
async function viewReview(reviewId, employeeId) {
    try {
        const response = await fetch(`api/reviews/${reviewId}`);
        if (!response.ok) throw new Error('Failed to load review');
        const review = await response.json();

        // Simple alert for view (or create modal if needed)
        alert(`Review Details:\nDate: ${review.review_date}\nType: ${review.template_type}\nStatus: ${review.status}\nFeedback: ${review.feedback || 'N/A'}\nGoals: ${JSON.stringify(review.goals || [])}`);
    } catch (error) {
        alert('Error viewing review: ' + error.message);
    }
}

// Edit Review
function editReview(reviewId) {
    // Fetch full review for prefill (assuming GET /api/reviews/:id exists, but use existing GET /:employee_id and filter, or add if needed)
    // For now, prompt for simplicity; in production, use modal
    const status = prompt('New status (draft/assigned/completed):');
    const feedback = prompt('New feedback:');
    const nextReviewDate = prompt('Next review date (YYYY-MM-DD):');

    if (!status && !feedback && !nextReviewDate) {
        alert('No changes provided');
        return;
    }

    const updates = {};
    if (status) updates.status = status;
    if (feedback) updates.feedback = feedback;
    if (nextReviewDate) updates.next_review_date = nextReviewDate;

    fetch(`api/reviews/${reviewId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Unauthorized');
            }
            return response.json().then(err => { throw new Error(err.error); });
        }
        return response.json();
    })
    .then(() => {
        // Refresh table - need employeeId, pass it or global
        const pathParts = window.location.pathname.split('/');
        const empId = pathParts[2];
        loadReviews(empId);
        alert('Review updated successfully');
    })
    .catch(error => {
        console.error('Edit error:', error);
        alert('Error: ' + error.message);
    });
}