if (window.location.pathname.endsWith('/leaves') && !window.location.pathname.endsWith('/request') && !window.location.pathname.endsWith('/pending')) {
    fetch('api/leaves/my-requests').then(res => res.json()).then(data => {
        const tbody = document.querySelector('#leaves-table tbody');
        data.forEach(leave => {
            const row = tbody.insertRow();
            row.innerHTML = `<td class='py-2 px-4 border'>${leave.start_date} to ${leave.end_date}</td><td class='py-2 px-4 border'>${leave.type}</td><td class='py-2 px-4 border'>${leave.status}</td>`;
        });
    }).catch(err => {
        document.getElementById('error-message').textContent = err.message;
        document.getElementById('error-message').classList.remove('hidden');
    });
}

if (window.location.pathname.endsWith('/leaves/pending')) {
    fetch('api/leaves/pending').then(res => res.json()).then(data => {
        const tbody = document.querySelector('#pending-table tbody');
        data.forEach(leave => {
            const row = tbody.insertRow();
            row.innerHTML = `<td class='py-2 px-4 border'>${leave.employee_name}</td><td class='py-2 px-4 border'>${leave.start_date} to ${leave.end_date}</td><td class='py-2 px-4 border'>${leave.type}</td><td class='py-2 px-4 border'><button onclick='approve(${leave.id})' class='bg-green-500 text-white px-2 py-1 rounded mr-2'>Approve</button><button onclick='reject(${leave.id})' class='bg-red-500 text-white px-2 py-1 rounded'>Reject</button></td>`;
        });
    }).catch(err => {
        document.getElementById('error-message').textContent = err.message;
        document.getElementById('error-message').classList.remove('hidden');
    });
}

if (document.getElementById('request-form')) {
    document.getElementById('request-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('start_date', document.getElementById('start_date').value);
        formData.append('end_date', document.getElementById('end_date').value);
        formData.append('type', document.getElementById('type').value);
        formData.append('reason', document.getElementById('reason').value);
        try {
            const res = await fetch('api/leaves/request', {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                window.location.href = 'leaves';
            } else {
                const errData = await res.json();
                document.getElementById('error-message').textContent = errData.error;
                document.getElementById('error-message').classList.remove('hidden');
            }
        } catch (err) {
            document.getElementById('error-message').textContent = 'Error submitting request';
            document.getElementById('error-message').classList.remove('hidden');
        }
    });
}

function approve(id) {
    fetch(`api/leaves/approve/${id}`, { method: 'POST' }).then(res => {
        if (res.ok) {
            location.reload();
        } else {
            alert('Error approving');
        }
    }).catch(() => alert('Error approving'));
}

function reject(id) {
    const reason = prompt('Reason for rejection:');
    if (!reason || reason.trim() === '') return;
    fetch(`api/leaves/reject/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason.trim() })
    }).then(res => {
        if (res.ok) {
            location.reload();
        } else {
            alert('Error rejecting');
        }
    }).catch(() => alert('Error rejecting'));
}