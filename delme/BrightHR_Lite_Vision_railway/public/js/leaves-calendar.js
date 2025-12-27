document.addEventListener('DOMContentLoaded', () => {
    let currentYear = new Date().getFullYear();
    let currentMonth = new Date().getMonth() + 1;

    updateMonthDisplay();
    fetchEmployees();
    fetchAndRenderCalendar({});

    // Event listeners
    document.getElementById('apply-filters').addEventListener('click', () => {
        const emp = document.getElementById('employee-filter').value;
        const typ = document.getElementById('type-filter').value;
        const filters = {};
        if (emp !== 'All Employees') filters.employee_name = emp;
        if (typ !== 'All Types') filters.type = typ;
        fetchAndRenderCalendar(filters);
    });

    document.getElementById('prev-month').addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        updateMonthDisplay();
        fetchAndRenderCalendar({});
    });

    document.getElementById('next-month').addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }
        updateMonthDisplay();
        fetchAndRenderCalendar({});
    });

    // Expose globals for badge clicks
    window.currentYear = currentYear;
    window.currentMonth = currentMonth;
});

let currentYear, currentMonth;

function fetchEmployees() {
    fetch('api/employees')
        .then(r => {
            if (!r.ok) throw new Error('Failed to fetch employees');
            return r.json();
        })
        .then(data => {
            const select = document.getElementById('employee-filter');
            select.innerHTML = '<option>All Employees</option>';
            data.employees.forEach(emp => {
                const opt = document.createElement('option');
                opt.value = emp.name;
                opt.textContent = emp.name;
                select.appendChild(opt);
            });
        })
        .catch(err => console.error('Error fetching employees:', err));
}

function fetchAndRenderCalendar(filters = {}) {
    const params = new URLSearchParams({
        year: currentYear,
        month: currentMonth,
        ...filters
    });
    fetch(`api/leaves/calendar?${params.toString()}`)
        .then(r => {
            if (!r.ok) throw new Error('Failed to fetch calendar events');
            return r.json();
        })
        .then(events => renderCalendar(currentYear, currentMonth, events))
        .catch(err => console.error('Error fetching calendar:', err));
}

function renderCalendar(year, month, events) {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = '';

    const firstDay = new Date(year, month - 1, 1).getDay(); // 0=Sun
    const daysInMonth = new Date(year, month, 0).getDate();
    const totalCells = 42; // 6 weeks

    // Empty cells before month starts
    for (let i = 0; i < firstDay; i++) {
        grid.appendChild(createEmptyCell());
    }

    // Days of the month
    for (let d = 1; d <= daysInMonth; d++) {
        const cell = createDayCell(d);
        const dayDate = new Date(year, month - 1, d);
        const dayEvents = events.filter(e => {
            const start = new Date(e.start_date);
            const end = new Date(e.end_date);
            return dayDate >= start && dayDate <= end;
        });

        dayEvents.forEach(ev => {
            const badge = createBadge(ev);
            badge.addEventListener('click', () => {
                alert(`Employee: ${ev.employee_name}\nType: ${ev.type}\nDates: ${ev.start_date} to ${ev.end_date}\nStatus: ${ev.status}`);
            });
            cell.appendChild(badge);
        });

        grid.appendChild(cell);
    }

    // Empty cells after month ends
    const cellsAfter = totalCells - (firstDay + daysInMonth);
    for (let i = 0; i < cellsAfter; i++) {
        grid.appendChild(createEmptyCell());
    }
}

function createEmptyCell() {
    const cell = document.createElement('div');
    cell.className = 'calendar-cell text-gray-400';
    cell.innerHTML = '&nbsp;';
    return cell;
}

function createDayCell(d) {
    const cell = document.createElement('div');
    cell.className = 'calendar-cell';
    const dayDiv = document.createElement('div');
    dayDiv.className = 'text-center text-sm font-medium text-gray-900 py-1';
    dayDiv.textContent = d;
    cell.appendChild(dayDiv);
    return cell;
}

function createBadge(ev) {
    const badge = document.createElement('span');
    badge.className = `leave-badge ${ev.color_code}-badge`;
    badge.textContent = `${ev.type.slice(0,4)} - ${ev.employee_name.split(' ')[0]}`;
    return badge;
}

function updateMonthDisplay() {
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('current-month').textContent = `${months[currentMonth - 1]} ${currentYear}`;
}