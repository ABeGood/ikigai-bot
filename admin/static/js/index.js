// Get React hooks
const { useState, useEffect } = React;

// Helper functions for date/time formatting
const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
};

const AdminDashboard = () => {
    const [reservations, setReservations] = useState([]);
    const [stats, setStats] = useState({ todayBookings: 0, pendingPayments: 0 });
    const [date, setDate] = useState(new Date());
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('all');
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [selectedReservation, setSelectedReservation] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetchReservations();
        fetchStats();
    }, [date]);

    const fetchReservations = async () => {
        setIsLoading(true);
        try {
            const dateStr = date.toISOString().split('T')[0];
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

    const filteredReservations = reservations.filter(reservation => {
        const matchesSearch = reservation.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            reservation.order_id.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFilter = filterType === 'all' ||
            (filterType === 'paid' && reservation.payed === 'True') ||
            (filterType === 'pending' && reservation.payed === 'False');
        return matchesSearch && matchesFilter;
    });

    return (
        <div className="min-h-screen bg-gray-50 p-4">
            <div className="max-w-7xl mx-auto">
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold text-gray-700 mb-2">Today's Bookings</h2>
                        <p className="text-3xl font-bold text-blue-600">{stats.todayBookings}</p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold text-gray-700 mb-2">Pending Payments</h2>
                        <p className="text-3xl font-bold text-yellow-600">{stats.pendingPayments}</p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold text-gray-700 mb-2">Select Date</h2>
                        <input
                            type="date"
                            value={date.toISOString().split('T')[0]}
                            onChange={(e) => setDate(new Date(e.target.value))}
                            className="w-full p-2 border border-gray-300 rounded"
                        />
                    </div>
                </div>

                {/* Main Content */}
                <div className="bg-white rounded-lg shadow">
                    <div className="p-6">
                        <h2 className="text-2xl font-bold text-gray-700 mb-6">Reservations</h2>

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
                                        filteredReservations.map((reservation) => (
                                            <tr key={reservation.order_id} className="border-b">
                                                <td className="p-3">
                                                    {formatTime(reservation.time_from)} -
                                                    {formatTime(reservation.time_to)}
                                                </td>
                                                <td className="p-3">{reservation.name}</td>
                                                <td className="p-3 capitalize">{reservation.type}</td>
                                                <td className="p-3">{reservation.place}</td>
                                                <td className="p-3">
                                                    <span className={`px-2 py-1 rounded-full text-sm ${reservation.payed === 'True'
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-yellow-100 text-yellow-800'
                                                        }`}>
                                                        {reservation.payed === 'True' ? 'Paid' : 'Pending'}
                                                    </span>
                                                </td>
                                                <td className="p-3">
                                                    <button
                                                        onClick={() => handleEdit(reservation)}
                                                        className="px-3 py-1 mr-2 bg-blue-100 text-blue-600 rounded"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(reservation.order_id)}
                                                        className="px-3 py-1 bg-red-100 text-red-600 rounded"
                                                    >
                                                        Delete
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
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
            </div>
        </div>
    );
};

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<AdminDashboard />);