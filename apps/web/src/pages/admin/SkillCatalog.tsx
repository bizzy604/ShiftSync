import React, { useMemo, useState } from 'react';
import { Loader2, Plus, Search, Trash2 } from 'lucide-react';

import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { useCreateSkill, useDeleteSkillCatalog, useSkills } from '../../lib/api/hooks';

export function SkillCatalog() {
    const [searchQuery, setSearchQuery] = useState('');
    const [newSkillName, setNewSkillName] = useState('');

    const { data: skills = [], isLoading } = useSkills();
    const createSkillMutation = useCreateSkill();
    const deleteSkillMutation = useDeleteSkillCatalog();

    const filtered = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) return skills;
        return skills.filter((skill) => skill.name.toLowerCase().includes(query));
    }, [skills, searchQuery]);

    const handleCreateSkill = () => {
        const name = newSkillName.trim();
        if (!name) return;
        createSkillMutation.mutate(
            { name },
            {
                onSuccess: () => setNewSkillName(''),
            }
        );
    };

    const handleDeleteSkill = (skillId: string, skillName: string) => {
        if (!window.confirm(`Delete skill "${skillName}"?`)) return;
        deleteSkillMutation.mutate(skillId);
    };

    return (
        <AppLayout title="Skill Catalog" role="admin" notificationCount={0}>
            <div className="p-4 md:p-6 max-w-4xl mx-auto">
                <div className="mb-6">
                    <p className="text-xs text-gray-500 mb-1">Admin &gt; Skill Catalog</p>
                    <h1 className="text-xl sm:text-2xl font-bold text-navy">Skill Catalog</h1>
                    <p className="text-sm text-gray-500 mt-1">Manage the predefined skills used for shifts and staff qualification.</p>
                </div>

                <div className="bg-white rounded-xl border border-border-gray shadow-sm p-4 mb-5">
                    <div className="flex items-center gap-3 flex-wrap">
                        <input
                            type="text"
                            value={newSkillName}
                            onChange={(event) => setNewSkillName(event.target.value)}
                            placeholder="Add skill (e.g. bartender)"
                            className="flex-1 w-full sm:w-auto min-w-0 sm:min-w-[220px] px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                        <button
                            onClick={handleCreateSkill}
                            disabled={createSkillMutation.isPending || newSkillName.trim().length === 0}
                            className="w-full sm:w-auto justify-center px-4 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2 disabled:opacity-50"
                        >
                            {createSkillMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                            Add Skill
                        </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                        Skills in use by users or shifts cannot be deleted.
                    </p>
                </div>

                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 w-full sm:w-auto min-w-0 sm:min-w-[220px] max-w-full sm:max-w-sm">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            placeholder="Search skills..."
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <span className="text-xs text-gray-500">{filtered.length} skills</span>
                </div>

                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    {isLoading ? (
                        <div className="py-16 flex flex-col items-center text-gray-400">
                            <Loader2 size={28} className="animate-spin mb-3" />
                            <p>Loading skills...</p>
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="py-16 text-center text-sm text-gray-500">No skills match this filter.</div>
                    ) : (
                        <div className="divide-y divide-border-gray">
                            {filtered.map((skill) => (
                                <div key={skill.id} className="px-4 md:px-5 py-3 flex items-center justify-between gap-3 flex-wrap">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <Badge variant="slate">Skill</Badge>
                                        <span className="text-sm font-semibold text-navy break-words">{skill.name}</span>
                                    </div>
                                    <button
                                        onClick={() => handleDeleteSkill(skill.id, skill.name)}
                                        disabled={deleteSkillMutation.isPending}
                                        className="p-2 rounded-lg text-gray-400 hover:text-danger hover:bg-danger/5 transition-base disabled:opacity-50"
                                        title={`Delete ${skill.name}`}
                                    >
                                        <Trash2 size={15} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    );
}
