import React, { useState } from 'react';
import { Search, Download, Edit, MoreHorizontal, ChevronLeft, ChevronRight, X, Mail, Check } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { SidePanel } from '../../components/SidePanel';
import { Modal } from '../../components/Modal';

/* ========== Mock Data ========== */

interface StaffMember {
    id: string;
    name: string;
    email: string;
    role: 'Staff' | 'Manager';
    locations: string[];
    skills: string[];
    status: 'Active' | 'Inactive';
}

const mockStaff: StaffMember[] = [
    { id: '1', name: 'Carlos M.', email: 'carlos@coastaleats.com', role: 'Staff', locations: ['Ocean Ave', 'Beach Blvd'], skills: ['Bartender'], status: 'Active' },
    { id: '2', name: 'Maria L.', email: 'maria@coastaleats.com', role: 'Staff', locations: ['Ocean Ave'], skills: ['Bartender', 'Server'], status: 'Active' },
    { id: '3', name: 'Jordan T.', email: 'jordan@coastaleats.com', role: 'Manager', locations: ['Ocean Ave'], skills: [], status: 'Active' },
    { id: '4', name: 'Sam K.', email: 'sam@coastaleats.com', role: 'Manager', locations: ['Beach Blvd', 'Downtown Miami'], skills: [], status: 'Active' },
    { id: '5', name: 'Priya N.', email: 'priya@coastaleats.com', role: 'Staff', locations: ['Miami Beach'], skills: ['Server'], status: 'Active' },
    { id: '6', name: 'Alex R.', email: 'alex@coastaleats.com', role: 'Staff', locations: ['Ocean Ave'], skills: ['Bartender'], status: 'Inactive' },
    { id: '7', name: 'Dana W.', email: 'dana@coastaleats.com', role: 'Manager', locations: ['Downtown Miami'], skills: [], status: 'Active' },
];

const allLocations = ['Ocean Ave', 'Beach Blvd', 'Miami Beach', 'Downtown Miami'];
const allSkills = ['Bartender', 'Server', 'Host', 'Cook', 'Supervisor'];

/* ========== Edit Staff Drawer ========== */

function EditStaffDrawer({ open, onClose, staff }: { open: boolean; onClose: () => void; staff: StaffMember | null }) {
    const [selectedSkills, setSelectedSkills] = useState<string[]>(staff?.skills ?? []);
    const [selectedLocations, setSelectedLocations] = useState<string[]>(staff?.locations ?? []);
    const [isActive, setIsActive] = useState(staff?.status === 'Active');

    if (!staff) return null;

    const toggleSkill = (skill: string) => {
        setSelectedSkills((prev) =>
            prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
        );
    };

    const toggleLocation = (loc: string) => {
        setSelectedLocations((prev) =>
            prev.includes(loc) ? prev.filter((l) => l !== loc) : [...prev, loc]
        );
    };

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title={`Edit — ${staff.name}`}
            subtitle={staff.email}
            width="w-[480px]"
            headerColor="bg-admin-slate"
        >
            <div className="p-6 space-y-6">
                {/* Name & Email */}
                <div className="space-y-3">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Name</label>
                        <input
                            type="text"
                            defaultValue={staff.name}
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

                {/* Role */}
                <div>
                    <label className="block text-sm font-medium text-navy mb-1.5">Role</label>
                    <select
                        defaultValue={staff.role}
                        className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-white text-sm text-navy focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                    >
                        <option value="Staff">Staff</option>
                        <option value="Manager">Manager</option>
                    </select>
                </div>

                {/* Skills */}
                <div>
                    <label className="block text-sm font-medium text-navy mb-2">Skills</label>
                    <div className="flex flex-wrap gap-2">
                        {allSkills.map((skill) => (
                            <button
                                key={skill}
                                onClick={() => toggleSkill(skill)}
                                className={`px-3 py-1.5 text-sm rounded-lg border transition-base ${selectedSkills.includes(skill)
                                        ? 'bg-admin-slate text-white border-admin-slate'
                                        : 'bg-white text-gray-600 border-border-gray hover:bg-gray-50'
                                    }`}
                            >
                                {selectedSkills.includes(skill) && <Check size={12} className="inline mr-1" />}
                                {skill}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Location Certifications */}
                <div>
                    <label className="block text-sm font-medium text-navy mb-2">Location Certifications</label>
                    <div className="space-y-2">
                        {allLocations.map((loc) => (
                            <label
                                key={loc}
                                className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border-gray hover:bg-gray-50 cursor-pointer transition-base"
                            >
                                <input
                                    type="checkbox"
                                    checked={selectedLocations.includes(loc)}
                                    onChange={() => toggleLocation(loc)}
                                    className="w-4 h-4 rounded border-border-gray text-admin-slate focus:ring-admin-slate"
                                />
                                <span className="text-sm text-navy">{loc}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Active/Inactive Toggle */}
                <div className="flex items-center justify-between px-3 py-3 bg-gray-50 rounded-lg">
                    <span className="text-sm font-medium text-navy">Account Status</span>
                    <button
                        onClick={() => setIsActive(!isActive)}
                        className={`relative w-11 h-6 rounded-full transition-colors ${isActive ? 'bg-success-light' : 'bg-gray-300'
                            }`}
                    >
                        <span
                            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${isActive ? 'translate-x-5' : 'translate-x-0'
                                }`}
                        />
                    </button>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4 border-t border-border-gray">
                    <button className="flex-1 py-2.5 bg-admin-slate text-white text-sm font-semibold rounded-lg hover:bg-admin-slate-light transition-base">
                        Save Changes
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

/* ========== Main Component ========== */

export function StaffManagement() {
    const [searchQuery, setSearchQuery] = useState('');
    const [editStaff, setEditStaff] = useState<StaffMember | null>(null);
    const [showInviteModal, setShowInviteModal] = useState(false);

    const filteredStaff = mockStaff.filter(
        (s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <AppLayout title="Staff Management" role="admin" notificationCount={0}>
            <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <p className="text-xs text-gray-500 mb-1">Admin › Staff Management</p>
                        <h1 className="text-2xl font-bold text-navy">Staff Management</h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowInviteModal(true)}
                            className="px-4 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base"
                        >
                            Invite Staff Member
                        </button>
                        <button className="px-4 py-2.5 border border-border-gray text-sm text-gray-700 rounded-lg hover:bg-gray-50 transition-base flex items-center gap-2">
                            <Download size={14} /> Export CSV
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 max-w-sm">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by name or email…"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Locations</option>
                    </select>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Skills</option>
                    </select>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Status</option>
                    </select>
                    <span className="text-xs text-gray-500">
                        Showing {filteredStaff.length} of {mockStaff.length} staff members
                    </span>
                </div>

                {/* Table */}
                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-50 border-b border-border-gray">
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Name</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Email</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Role</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Locations</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Skills</th>
                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Status</th>
                                    <th className="px-5 py-3 text-right text-xs font-bold text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredStaff.map((s) => (
                                    <tr key={s.id} className="border-b border-border-gray hover:bg-gray-50 transition-base">
                                        <td className="px-5 py-3.5">
                                            <div className="flex items-center gap-2.5">
                                                <Avatar name={s.name} size="sm" color={s.status === 'Inactive' ? 'bg-gray-400' : 'bg-admin-slate'} />
                                                <span className="text-sm font-medium text-navy">{s.name}</span>
                                            </div>
                                        </td>
                                        <td className="px-5 py-3.5 text-sm text-gray-600">{s.email}</td>
                                        <td className="px-5 py-3.5 text-sm text-gray-700">{s.role}</td>
                                        <td className="px-5 py-3.5">
                                            <div className="flex flex-wrap gap-1">
                                                {s.locations.map((loc) => (
                                                    <Badge key={loc} variant="gray">{loc}</Badge>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {s.skills.length > 0 ? (
                                                <div className="flex flex-wrap gap-1">
                                                    {s.skills.map((skill) => (
                                                        <Badge key={skill} variant="slate">{skill}</Badge>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span className="text-xs text-gray-400">—</span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <Badge variant={s.status === 'Active' ? 'green' : 'gray'}>{s.status}</Badge>
                                        </td>
                                        <td className="px-5 py-3.5 text-right">
                                            <div className="flex items-center justify-end gap-1">
                                                <button
                                                    onClick={() => setEditStaff(s)}
                                                    className="p-2 rounded-lg text-gray-400 hover:text-navy hover:bg-gray-100 transition-base"
                                                    title="Edit"
                                                >
                                                    <Edit size={15} />
                                                </button>
                                                <button className="p-2 rounded-lg text-gray-400 hover:text-navy hover:bg-gray-100 transition-base">
                                                    <MoreHorizontal size={15} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    <div className="px-5 py-3 bg-gray-50 border-t border-border-gray flex items-center justify-between">
                        <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base">
                            <ChevronLeft size={16} /> Prev
                        </button>
                        <span className="text-sm text-gray-600">Page 1 of 5</span>
                        <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base">
                            Next <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Edit Staff Drawer */}
            <EditStaffDrawer
                open={editStaff !== null}
                onClose={() => setEditStaff(null)}
                staff={editStaff}
            />

            {/* Invite Staff Modal */}
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
                        <button className="px-5 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2">
                            <Mail size={14} /> Send Invite
                        </button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Email</label>
                        <input
                            type="email"
                            placeholder="newstaff@coastaleats.com"
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Role</label>
                        <select className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-white text-sm text-navy">
                            <option>Staff</option>
                            <option>Manager</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-2">Location Assignment</label>
                        <div className="space-y-2">
                            {allLocations.map((loc) => (
                                <label
                                    key={loc}
                                    className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border-gray hover:bg-gray-50 cursor-pointer transition-base"
                                >
                                    <input type="checkbox" className="w-4 h-4 rounded border-border-gray text-admin-slate" />
                                    <span className="text-sm text-navy">{loc}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <p className="text-xs text-blue-700">
                            The invited person will receive an email with instructions to set their password.
                        </p>
                    </div>
                </div>
            </Modal>
        </AppLayout>
    );
}
