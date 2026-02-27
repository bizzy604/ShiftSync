import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    Check,
    ChevronLeft,
    ChevronRight,
    Download,
    Edit,
    Loader2,
    Mail,
    Search,
    Shield,
    Trash2,
    X,
} from 'lucide-react';

import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { SidePanel } from '../../components/SidePanel';
import { Modal } from '../../components/Modal';
import {
    useCreateUser,
    useDeleteUser,
    useLocations,
    useUpdateUser,
    useUsers,
} from '../../lib/api/hooks';
import { UserResponse } from '../../lib/api/types';

function buildCsvValue(raw: string): string {
    const escaped = raw.replace(/"/g, '""');
    return `"${escaped}"`;
}

function downloadCsv(filename: string, headers: string[], rows: string[][]): void {
    const headerLine = headers.map(buildCsvValue).join(',');
    const body = rows
        .map((row) => row.map((cell) => buildCsvValue(cell)).join(','))
        .join('\n');
    const csv = `${headerLine}\n${body}\n`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function EditStaffDrawer({ open, onClose, staff }: { open: boolean; onClose: () => void; staff: UserResponse | null }) {
    const updateMutation = useUpdateUser();
    const deleteMutation = useDeleteUser();

    const [name, setName] = useState(staff?.name ?? '');
    const [role, setRole] = useState(staff?.role ?? 'staff');
    const [isActive, setIsActive] = useState(staff?.is_active ?? true);

    useEffect(() => {
        if (staff) {
            setName(staff.name);
            setRole(staff.role);
            setIsActive(staff.is_active);
        }
    }, [staff]);

    if (!staff) return null;

    const handleSave = () => {
        updateMutation.mutate(
            {
                id: staff.id,
                data: { name, role: role as any, is_active: isActive },
            },
            {
                onSuccess: () => onClose(),
            }
        );
    };

    const handleDeactivate = () => {
        if (window.confirm(`Are you sure you want to deactivate ${staff.name}?`)) {
            deleteMutation.mutate(staff.id, {
                onSuccess: () => onClose(),
            });
        }
    };

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title={`Edit - ${staff.name}`}
            subtitle={staff.email}
            width="sm:w-[480px]"
            headerColor="bg-admin-slate"
        >
            <div className="p-6 space-y-6">
                <div className="space-y-3">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Email</label>
                        <input
                            type="email"
                            value={staff.email}
                            readOnly
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-100 text-sm text-gray-500 cursor-not-allowed"
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-navy mb-1.5">Role</label>
                    <div className="flex gap-2">
                        {['staff', 'manager', 'admin'].map((candidateRole) => (
                            <button
                                key={candidateRole}
                                onClick={() => setRole(candidateRole as any)}
                                className={`flex-1 py-2 text-sm font-medium rounded-lg border transition-base capitalize ${role === candidateRole
                                    ? 'bg-admin-slate text-white border-admin-slate'
                                    : 'bg-white text-gray-600 border-border-gray hover:bg-gray-50'
                                    }`}
                            >
                                {candidateRole}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-xl border border-border-gray/50">
                    <div className="flex items-center gap-2">
                        <Shield size={16} className={isActive ? 'text-success' : 'text-gray-400'} />
                        <span className="text-sm font-medium text-navy">Account Active</span>
                    </div>
                    <button
                        onClick={() => setIsActive((prev) => !prev)}
                        className={`relative w-11 h-6 rounded-full transition-colors ${isActive ? 'bg-success-light' : 'bg-gray-300'
                            }`}
                    >
                        <span
                            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${isActive ? 'translate-x-5' : 'translate-x-0'
                                }`}
                        />
                    </button>
                </div>

                <div className="pt-4 border-t border-border-gray">
                    <button
                        onClick={handleDeactivate}
                        className="w-full flex items-center justify-center gap-2 py-2.5 text-sm font-bold text-danger hover:bg-danger/5 rounded-lg transition-base border border-transparent hover:border-danger/20"
                    >
                        <Trash2 size={16} /> Deactivate Account
                    </button>
                </div>

                <div className="flex gap-3 pt-4">
                    <button
                        onClick={handleSave}
                        disabled={updateMutation.isPending}
                        className="flex-1 py-2.5 bg-admin-slate text-white text-sm font-semibold rounded-lg hover:bg-admin-slate-light transition-base disabled:opacity-50"
                    >
                        {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 text-sm text-gray-600 border border-border-gray rounded-lg hover:bg-gray-50 transition-base"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </SidePanel>
    );
}

export function StaffManagement() {
    const [searchParams] = useSearchParams();
    const defaultLocation = searchParams.get('location_id') ?? 'all';

    const [searchQuery, setSearchQuery] = useState('');
    const [editStaff, setEditStaff] = useState<UserResponse | null>(null);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteName, setInviteName] = useState('');
    const [inviteRole, setInviteRole] = useState<'staff' | 'manager' | 'admin'>('staff');
    const [selectedLocationId, setSelectedLocationId] = useState(defaultLocation);
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
    const [page, setPage] = useState(1);

    const includeInactive = statusFilter !== 'active';
    const locationFilter = selectedLocationId === 'all' ? undefined : selectedLocationId;

    const { data: usersData, isLoading } = useUsers(locationFilter, includeInactive);
    const { data: locationsData } = useLocations();
    const inviteMutation = useCreateUser();
    const quickUpdateMutation = useUpdateUser();

    const staff = usersData?.users || [];

    const filteredStaff = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        return staff.filter((user) => {
            const matchesSearch =
                query.length === 0 ||
                user.name.toLowerCase().includes(query) ||
                user.email.toLowerCase().includes(query);
            const matchesStatus =
                statusFilter === 'all' ||
                (statusFilter === 'active' && user.is_active) ||
                (statusFilter === 'inactive' && !user.is_active);
            return matchesSearch && matchesStatus;
        });
    }, [staff, searchQuery, statusFilter]);

    const pageSize = 15;
    const totalPages = Math.max(1, Math.ceil(filteredStaff.length / pageSize));
    const pageStart = (page - 1) * pageSize;
    const pagedStaff = filteredStaff.slice(pageStart, pageStart + pageSize);

    useEffect(() => {
        setPage(1);
    }, [searchQuery, selectedLocationId, statusFilter]);

    useEffect(() => {
        if (page > totalPages) {
            setPage(totalPages);
        }
    }, [page, totalPages]);

    const handleInvite = () => {
        inviteMutation.mutate(
            {
                name: inviteName,
                email: inviteEmail,
                role: inviteRole,
                password: 'temporary-password-123',
            },
            {
                onSuccess: () => {
                    setShowInviteModal(false);
                    setInviteEmail('');
                    setInviteName('');
                    setInviteRole('staff');
                },
            }
        );
    };

    const handleToggleActive = (user: UserResponse) => {
        quickUpdateMutation.mutate({
            id: user.id,
            data: { is_active: !user.is_active },
        });
    };

    const handleExportCsv = () => {
        const rows = filteredStaff.map((user) => [
            user.name,
            user.email,
            user.role,
            user.is_active ? 'active' : 'inactive',
            user.home_timezone ?? '',
            String(user.desired_hours_per_week ?? ''),
            user.hourly_rate != null ? String(user.hourly_rate) : '',
            user.created_at,
        ]);
        downloadCsv(
            `staff_export_${new Date().toISOString().slice(0, 10)}.csv`,
            ['name', 'email', 'role', 'status', 'home_timezone', 'desired_hours_per_week', 'hourly_rate', 'created_at'],
            rows
        );
    };

    return (
        <AppLayout title="Staff Management" role="admin" notificationCount={0}>
            <div className="p-4 md:p-6">
                <div className="flex items-start justify-between mb-6 gap-3 flex-wrap">
                    <div>
                        <p className="text-xs text-gray-500 mb-1">Admin &gt; Staff Management</p>
                        <h1 className="text-2xl font-bold text-navy">Staff Management</h1>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                        <button
                            onClick={() => setShowInviteModal(true)}
                            className="px-4 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base"
                        >
                            Invite Staff Member
                        </button>
                        <button
                            onClick={handleExportCsv}
                            disabled={filteredStaff.length === 0}
                            className="px-4 py-2.5 border border-border-gray text-sm text-gray-700 rounded-lg hover:bg-gray-50 transition-base flex items-center gap-2 disabled:opacity-50"
                        >
                            <Download size={14} /> Export CSV
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 min-w-[220px] max-w-sm">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by name or email..."
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>

                    <select
                        value={selectedLocationId}
                        onChange={(event) => setSelectedLocationId(event.target.value)}
                        className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Locations</option>
                        {locationsData?.locations.map((location) => (
                            <option key={location.id} value={location.id}>
                                {location.name}
                            </option>
                        ))}
                    </select>

                    <select
                        value={statusFilter}
                        onChange={(event) => setStatusFilter(event.target.value as 'all' | 'active' | 'inactive')}
                        className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Status</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                    </select>

                    <span className="text-xs text-gray-500">
                        Showing {filteredStaff.length} of {staff.length} users
                    </span>
                </div>

                {isLoading && (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <Loader2 size={32} className="animate-spin mb-4" />
                        <p>Fetching staff directory...</p>
                    </div>
                )}

                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[860px]">
                            <thead>
                                <tr className="bg-gray-50 border-b border-border-gray">
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Name</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Email</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Role</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Timezone</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Desired Hrs</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Status</th>
                                    <th className="px-5 py-3 text-right text-xs font-bold text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pagedStaff.map((user) => (
                                    <tr key={user.id} className="border-b border-border-gray hover:bg-gray-50 transition-base">
                                        <td className="px-5 py-3.5">
                                            <div className="flex items-center gap-2.5">
                                                <Avatar name={user.name} size="sm" color={!user.is_active ? 'bg-gray-400' : 'bg-admin-slate'} />
                                                <span className="text-sm font-medium text-navy">{user.name}</span>
                                            </div>
                                        </td>
                                        <td className="px-5 py-3.5 text-sm text-gray-600">{user.email}</td>
                                        <td className="px-5 py-3.5 text-sm text-gray-700 capitalize">{user.role}</td>
                                        <td className="px-5 py-3.5 text-xs text-gray-600">{user.home_timezone}</td>
                                        <td className="px-5 py-3.5 text-xs font-bold text-navy">{user.desired_hours_per_week}</td>
                                        <td className="px-5 py-3.5">
                                            <Badge variant={user.is_active ? 'green' : 'gray'}>
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </Badge>
                                        </td>
                                        <td className="px-5 py-3.5 text-right">
                                            <div className="flex items-center justify-end gap-1">
                                                <button
                                                    onClick={() => setEditStaff(user)}
                                                    className="p-2 rounded-lg text-gray-400 hover:text-navy hover:bg-gray-100 transition-base"
                                                    title="Edit user"
                                                >
                                                    <Edit size={15} />
                                                </button>
                                                <button
                                                    onClick={() => handleToggleActive(user)}
                                                    disabled={quickUpdateMutation.isPending}
                                                    className={`p-2 rounded-lg transition-base disabled:opacity-50 ${user.is_active
                                                        ? 'text-gray-400 hover:text-danger hover:bg-danger/5'
                                                        : 'text-gray-400 hover:text-success hover:bg-success/5'
                                                        }`}
                                                    title={user.is_active ? 'Deactivate user' : 'Activate user'}
                                                >
                                                    {user.is_active ? <Trash2 size={15} /> : <Check size={15} />}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {!isLoading && pagedStaff.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="px-5 py-10 text-center text-sm text-gray-500">
                                            No users match the selected filters.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="px-5 py-3 bg-gray-50 border-t border-border-gray flex items-center justify-between">
                        <button
                            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                            disabled={page === 1}
                            className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                        >
                            <ChevronLeft size={16} /> Prev
                        </button>
                        <span className="text-sm text-gray-600">
                            Page {page} of {totalPages}
                        </span>
                        <button
                            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                            disabled={page >= totalPages}
                            className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                        >
                            Next <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            </div>

            <EditStaffDrawer
                open={editStaff !== null}
                onClose={() => setEditStaff(null)}
                staff={editStaff}
            />

            <Modal
                open={showInviteModal}
                onClose={() => setShowInviteModal(false)}
                title="Invite Staff Member"
                width="max-w-md"
                footer={
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={() => setShowInviteModal(false)}
                            className="px-4 py-2 text-sm text-gray-600 hover:text-navy transition-base"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleInvite}
                            disabled={inviteMutation.isPending || !inviteEmail || !inviteName}
                            className="px-5 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2 disabled:opacity-50"
                        >
                            <Mail size={14} />
                            {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
                        </button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Full Name</label>
                        <input
                            type="text"
                            placeholder="Alex Smith"
                            value={inviteName}
                            onChange={(event) => setInviteName(event.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Email Address</label>
                        <input
                            type="email"
                            placeholder="alex@coastaleats.com"
                            value={inviteEmail}
                            onChange={(event) => setInviteEmail(event.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Role</label>
                        <div className="flex gap-2">
                            {(['staff', 'manager', 'admin'] as const).map((candidateRole) => (
                                <button
                                    key={candidateRole}
                                    onClick={() => setInviteRole(candidateRole)}
                                    className={`flex-1 py-2 text-xs font-bold rounded-lg border transition-base capitalize ${inviteRole === candidateRole
                                        ? 'bg-admin-slate text-white border-admin-slate'
                                        : 'bg-white text-gray-500 border-border-gray hover:bg-gray-50'
                                        }`}
                                >
                                    {candidateRole}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <p className="text-[11px] text-blue-700 leading-relaxed">
                            A temporary password is generated for new invites. Ask the user to change it after first login.
                        </p>
                    </div>
                </div>
            </Modal>
        </AppLayout>
    );
}
