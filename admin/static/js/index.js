// Get React hooks
const { useState, useEffect } = React;

const TIMEZONE = 'Europe/Prague';

const isExpired = (reservation) => {
    const now = new Date();
    const reservationStart = new Date(reservation.time_from);
    return reservationStart < now;
};

// Helper functions for date/time formatting
const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
};

const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        timeZone: TIMEZONE
    });
};

const formatDisplayDate = (date) => {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
};

const StatsCard = ({ reservations, date }) => {
    // Filter reservations for selected date and calculate stats
    const selectedDateReservations = reservations.filter(res => {
        const resDate = new Date(res.day);
        return resDate.getDate() === date.getDate() &&
            resDate.getMonth() === date.getMonth() &&
            resDate.getFullYear() === date.getFullYear();
    });

    // Count non-expired bookings
    const activeBookings = selectedDateReservations.filter(res => !isExpired(res)).length;

    // Count and filter pending payments
    const pendingPayments = selectedDateReservations.filter(res => (res.payed === 'No' || res.payed === 'Pending'));
    const pendingPaymentsCount = pendingPayments.length;

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="border-b pb-4 mb-4">
                <h2 className="text-xl font-bold text-gray-700 mb-4">
                    Overview for {formatDisplayDate(date)}
                </h2>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-sm text-gray-600">Active Bookings</p>
                        <p className="text-3xl font-bold text-blue-600">{activeBookings}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-600">Pending Payments</p>
                        <p className="text-3xl font-bold text-yellow-600">{pendingPaymentsCount}</p>
                    </div>
                </div>
            </div>

            {pendingPaymentsCount > 0 && (
                <div>
                    <h3 className="text-md font-semibold text-gray-700 mb-3">
                        Pending Payments
                    </h3>
                    <div className="max-h-40 overflow-y-auto">
                        <table className="w-full text-sm">
                            <thead className="text-gray-600">
                                <tr>
                                    <th className="text-left py-2">Client</th>
                                    <th className="text-left py-2">Time</th>
                                    <th className="text-left py-2">Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pendingPayments.map(res => (
                                    <tr key={res.order_id} className="border-t">
                                        <td className="py-2">{res.name}</td>
                                        <td className="py-2">
                                            {formatTime(res.time_from)} - {formatTime(res.time_to)}
                                        </td>
                                        <td className="py-2">{res.period * 20} CZK</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

const Calendar = ({ date, onDateChange }) => {
    const generateCalendarDays = () => {
        const firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        const startDayOfWeek = firstDay.getDay() || 7; // Convert Sunday (0) to 7

        const days = [];
        // Add empty cells for days before the first day of month
        for (let i = 1; i < startDayOfWeek; i++) {
            days.push(<div key={`empty-${i}`} className="p-2" />);
        }

        // Add the days of the month
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const currentDate = new Date(date.getFullYear(), date.getMonth(), day);
            const isSelected = currentDate.getDate() === date.getDate();
            const isToday = currentDate.toDateString() === new Date().toDateString();

            days.push(
                <button
                    key={day}
                    onClick={() => onDateChange(currentDate)}
                    className={`p-2 w-full text-center rounded hover:bg-blue-50 ${isSelected ? 'bg-blue-500 text-white hover:bg-blue-600' : ''
                        } ${isToday && !isSelected ? 'border border-blue-500' : ''}`}
                >
                    {day}
                </button>
            );
        }
        return days;
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <button
                    onClick={() => {
                        const newDate = new Date(date);
                        newDate.setMonth(newDate.getMonth() - 1);
                        onDateChange(newDate);
                    }}
                    className="p-1 hover:bg-gray-100 rounded"
                >
                    ←
                </button>
                <span className="font-semibold">
                    {date.toLocaleString('default', { month: 'long', year: 'numeric' })}
                </span>
                <button
                    onClick={() => {
                        const newDate = new Date(date);
                        newDate.setMonth(newDate.getMonth() + 1);
                        onDateChange(newDate);
                    }}
                    className="p-1 hover:bg-gray-100 rounded"
                >
                    →
                </button>
            </div>

            <div className="grid grid-cols-7 gap-1 mb-2">
                {['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].map(day => (
                    <div key={day} className="text-center text-sm font-semibold text-gray-600">
                        {day}
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
                {generateCalendarDays()}
            </div>
        </div>
    );
};

const TimeTable = ({ reservations, date, workdayStart = 9, workdayEnd = 21 }) => {
    // Generate time slots
    const timeSlots = [];
    for (let hour = workdayStart; hour <= workdayEnd; hour++) {
        timeSlots.push(`${String(hour).padStart(2, '0')}:00`);
        timeSlots.push(`${String(hour).padStart(2, '0')}:30`);
    }

    // Filter reservations for selected date
    const dayReservations = reservations.filter(res => {
        const resDate = new Date(res.day);
        return resDate.getDate() === date.getDate() &&
            resDate.getMonth() === date.getMonth() &&
            resDate.getFullYear() === date.getFullYear();
    });

    // Calculate position and height for reservation blocks
    const getReservationStyle = (reservation) => {
        const startTime = new Date(reservation.time_from);
        const endTime = new Date(reservation.time_to);

        const startMinutes = startTime.getHours() * 60 + startTime.getMinutes();
        const endMinutes = endTime.getHours() * 60 + endTime.getMinutes();
        const dayStartMinutes = workdayStart * 60;

        const top = ((startMinutes - dayStartMinutes) / 30) * 40; // 40px per half hour
        const height = ((endMinutes - startMinutes) / 30) * 40;

        return {
            top: `${top}px`,
            height: `${height}px`
        };
    };

    return (
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
            {/* Tabs */}
            <div className="flex sm:hidden mb-4">
                <button className="px-4 py-2 font-medium text-gray-600 hover:text-gray-800">List</button>
                <button className="px-4 py-2 font-medium text-blue-600 border-b-2 border-blue-600">Timetable</button>
            </div>

            {/* Timetable */}
            <div className="bg-white rounded-lg shadow flex-1">
                <div className="p-4 border-b">
                    <h3 className="text-lg font-semibold">Schedule for {formatDate(date)}</h3>
                </div>
                <div className="relative p-4" style={{ height: `${(workdayEnd - workdayStart + 1) * 80}px` }}>
                    {/* Time slots */}
                    <div className="absolute top-0 left-0 w-16 h-full border-r">
                        {timeSlots.map((time, index) => (
                            <div
                                key={time}
                                className="text-sm text-gray-600 absolute"
                                style={{ top: `${index * 40 - 10}px` }}
                            >
                                {time}
                            </div>
                        ))}
                    </div>

                    {/* Grid lines */}
                    <div className="absolute left-16 right-0 top-0 h-full">
                        {timeSlots.map((_, index) => (
                            <div
                                key={index}
                                className="absolute w-full border-t border-gray-100"
                                style={{ top: `${index * 40}px` }}
                            />
                        ))}
                    </div>

                    {/* Reservation blocks */}
                    <div className="absolute left-16 right-0 top-0">
                        {dayReservations.map(reservation => {
                            const style = getReservationStyle(reservation);
                            const isExpired = new Date(reservation.time_to) < new Date();

                            return (
                                <div
                                    key={reservation.order_id}
                                    className={`absolute left-4 right-4 rounded p-2 ${isExpired ? 'bg-gray-100' :
                                            reservation.payed === 'True' ? 'bg-green-100' : 'bg-yellow-100'
                                        }`}
                                    style={style}
                                >
                                    <div className="text-sm font-medium">{reservation.name}</div>
                                    <div className="text-xs">
                                        Place {reservation.place} • {reservation.type}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

const AdminDashboard = () => {
    const [reservations, setReservations] = useState([]);
    const [stats, setStats] = useState({ todayBookings: 0, pendingPayments: 0 });
    const [date, setDate] = useState(new Date());
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('all');
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [viewMode, setViewMode] = useState('list'); // 'list' or 'timetable'
    const [selectedReservation, setSelectedReservation] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showExpired, setShowExpired] = useState(true);

    useEffect(() => {
        fetchReservations();
        fetchStats();
    }, [date]);

    const filteredReservations = reservations.filter(reservation => {
        const matchesSearch = reservation.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            reservation.order_id.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFilter = filterType === 'all' ||
            (filterType === 'paid' && reservation.payed === 'True') ||
            (filterType === 'pending' && reservation.payed === 'False');
        const matchesExpired = showExpired || !isExpired(reservation);
        return matchesSearch && matchesFilter && matchesExpired;
    });

    const fetchReservations = async () => {
        setIsLoading(true);
        try {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;

            const response = await fetch(`/api/reservations?date=${dateStr}`);
            if (!response.ok) throw new Error('Failed to fetch reservations');
            const data = await response.json();
            setReservations(data);
        } catch (error) {
            console.error('Error fetching reservations:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            const data = await response.json();
            setStats(data);
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    };

    const handleDelete = async (orderId) => {
        if (!window.confirm('Are you sure you want to delete this reservation?')) return;
        try {
            const response = await fetch(`/api/reservations/${orderId}`, {
                method: 'DELETE',
            });
            if (!response.ok) throw new Error('Failed to delete reservation');
            fetchReservations();
        } catch (error) {
            console.error('Error deleting reservation:', error);
        }
    };

    const handleEdit = (reservation) => {
        setSelectedReservation(reservation);
        setIsEditModalOpen(true);
    };

    const handleSave = async () => {
        try {
            const response = await fetch(`/api/reservations/${selectedReservation.order_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(selectedReservation),
            });
            if (!response.ok) throw new Error('Failed to update reservation');
            setIsEditModalOpen(false);
            fetchReservations();
        } catch (error) {
            console.error('Error updating reservation:', error);
        }
    };

    const handleCloseModal = () => {
        setIsEditModalOpen(false);
        setSelectedReservation(null);
    };

    return (
        <div className="min-h-screen bg-gray-50 p-4">
            <div className="max-w-7xl mx-auto">
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <StatsCard
                        reservations={reservations}
                        date={date}
                    />

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex justify-between items-center mb-2">
                            <h2 className="text-xl font-bold text-gray-700">Select Date</h2>
                            <button
                                onClick={() => setDate(new Date())}
                                className="px-3 py-1 text-sm bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                            >
                                Today
                            </button>
                        </div>
                        <Calendar date={date} onDateChange={setDate} />
                    </div>
                </div>

                {/* Main Content */}
                <div className="bg-white rounded-lg shadow">
                    <div className="p-6">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-2xl font-bold text-gray-700">Reservations</h2>
                            <div className="flex items-center gap-4">
                                <div className="flex border rounded overflow-hidden">
                                    <button
                                        className={`px-4 py-2 ${viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-gray-600'}`}
                                        onClick={() => setViewMode('list')}
                                    >
                                        List
                                    </button>
                                    <button
                                        className={`px-4 py-2 ${viewMode === 'timetable' ? 'bg-blue-50 text-blue-600' : 'text-gray-600'}`}
                                        onClick={() => setViewMode('timetable')}
                                    >
                                        Timetable
                                    </button>
                                </div>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={showExpired}
                                        onChange={(e) => setShowExpired(e.target.checked)}
                                        className="form-checkbox h-5 w-5 text-blue-600"
                                    />
                                    <span>Show Past Reservations</span>
                                </label>
                            </div>
                        </div>

                        {/* Search and Filter */}
                        <div className="flex flex-col sm:flex-row gap-4 mb-6">
                            <input
                                type="text"
                                placeholder="Search by name or order ID..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="flex-1 p-2 border border-gray-300 rounded"
                            />
                            <select
                                value={filterType}
                                onChange={(e) => setFilterType(e.target.value)}
                                className="sm:w-48 p-2 border border-gray-300 rounded"
                            >
                                <option value="all">All Reservations</option>
                                <option value="paid">Paid Only</option>
                                <option value="pending">Pending Payment</option>
                            </select>
                        </div>

                        {/* Table */}
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-gray-50">
                                        <th className="text-left p-3 border-b">Date</th>
                                        <th className="text-left p-3 border-b">Time</th>
                                        <th className="text-left p-3 border-b">Client</th>
                                        <th className="text-left p-3 border-b">Service</th>
                                        <th className="text-left p-3 border-b">Place</th>
                                        <th className="text-left p-3 border-b">Status</th>
                                        <th className="text-left p-3 border-b">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {isLoading ? (
                                        <tr>
                                            <td colSpan={6} className="text-center p-4">Loading...</td>
                                        </tr>
                                    ) : filteredReservations.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="text-center p-4">No reservations found</td>
                                        </tr>
                                    ) : (
                                        filteredReservations.map((reservation) => {
                                            const expired = isExpired(reservation);
                                            return (
                                                <tr
                                                    key={reservation.order_id}
                                                    className={`border-b ${expired ? 'text-gray-400' : ''}`}
                                                >
                                                    <td className="p-3">{formatDate(reservation.time_from)}</td>
                                                    <td className="p-3">
                                                        {formatTime(reservation.time_from)} -
                                                        {formatTime(reservation.time_to)}
                                                    </td>
                                                    <td className="p-3">{reservation.name}</td>
                                                    <td className="p-3">{reservation.type}</td>
                                                    <td className="p-3">{reservation.place}</td>
                                                    <td className="p-3">
                                                        <span className={`px-2 py-1 rounded-full text-sm ${expired ? 'bg-gray-100 text-gray-600' :
                                                                reservation.payed === 'True' ? 'bg-green-100 text-green-800' :
                                                                    'bg-yellow-100 text-yellow-800'
                                                            }`}>
                                                            {expired ? 'Expired' :
                                                                reservation.payed === 'True' ? 'Paid' : 'Pending'}
                                                        </span>
                                                    </td>
                                                    <td className="p-3">
                                                        <button
                                                            onClick={() => handleEdit(reservation)}
                                                            className={`px-3 py-1 mr-2 rounded ${expired ? 'bg-gray-100 text-gray-600' : 'bg-blue-100 text-blue-600'
                                                                }`}
                                                        >
                                                            Edit
                                                        </button>
                                                        <button
                                                            onClick={() => handleDelete(reservation.order_id)}
                                                            className={`px-3 py-1 rounded ${expired ? 'bg-gray-100 text-gray-600' : 'bg-red-100 text-red-600'
                                                                }`}
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Edit Modal */}
                {isEditModalOpen && selectedReservation && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                        <div className="bg-white p-6 rounded-lg max-w-md w-full">
                            <h2 className="text-xl font-bold mb-4">Edit Reservation</h2>
                            <div className="mb-4">
                                <label className="block mb-2">Client Name</label>
                                <input
                                    type="text"
                                    value={selectedReservation.name}
                                    onChange={(e) => setSelectedReservation({
                                        ...selectedReservation,
                                        name: e.target.value
                                    })}
                                    className="w-full p-2 border rounded"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block mb-2">Payment Status</label>
                                <select
                                    value={selectedReservation.payed}
                                    onChange={(e) => setSelectedReservation({
                                        ...selectedReservation,
                                        payed: e.target.value
                                    })}
                                    className="w-full p-2 border rounded"
                                >
                                    <option value="True">Paid</option>
                                    <option value="False">Pending</option>
                                </select>
                            </div>
                            <div className="flex justify-end gap-2">
                                <button
                                    onClick={handleCloseModal}
                                    className="px-4 py-2 bg-gray-200 rounded"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSave}
                                    className="px-4 py-2 bg-blue-500 text-white rounded"
                                >
                                    Save changes
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* View content */}
                {viewMode === 'list' ? (
                    <div className="overflow-x-auto">
                        {/* ... existing table ... */}
                    </div>
                ) : (
                    <TimeTable
                        reservations={filteredReservations}
                        date={date}
                        workdayStart={9}
                        workdayEnd={21}
                    />
                )}
            </div>
        </div>
    );
};

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<AdminDashboard />);