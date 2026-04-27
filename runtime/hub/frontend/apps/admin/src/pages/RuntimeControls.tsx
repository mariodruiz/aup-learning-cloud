// Copyright (C) 2025 Advanced Micro Devices, Inc. All rights reserved.
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { useCallback, useEffect, useState } from 'react';
import { Alert, Badge, Button, Card, Form, Modal, Spinner, Table } from 'react-bootstrap';
import type { GroupLifecyclePolicy, ResourceAccessPolicy, RuntimeControlsGroup, RuntimeControlsResource, RuntimeOverlay } from '@auplc/shared';
import { getRuntimeControls, resetRuntimeOverlay, setRuntimeOverlay } from '@auplc/shared';

type Section = 'groups' | 'resources';

function groupLifecycleKey(groupName: string): string { return `groups.${groupName}.lifecycle`; }
function resourceAccessKey(resourceKey: string): string { return `resources.${resourceKey}.access`; }
function overlayFor(overlays: RuntimeOverlay[], key: string): RuntimeOverlay | undefined { return overlays.find(overlay => overlay.key === key); }

export function RuntimeControls() {
  const [groups, setGroups] = useState<RuntimeControlsGroup[]>([]);
  const [resources, setResources] = useState<RuntimeControlsResource[]>([]);
  const [overlays, setOverlays] = useState<RuntimeOverlay[]>([]);
  const [section, setSection] = useState<Section>('groups');
  const [editingGroup, setEditingGroup] = useState<RuntimeControlsGroup | null>(null);
  const [editingResource, setEditingResource] = useState<RuntimeControlsResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getRuntimeControls();
      setGroups(response.groups);
      setResources(response.resources);
      setOverlays(response.overrides);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runtime controls');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveOverlay = useCallback(async (key: string, value: Record<string, unknown>, reason: string, expectedRevision?: number) => {
    try {
      setSaving(true);
      setError(null);
      await setRuntimeOverlay(key, value, reason, expectedRevision);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save runtime overlay');
    } finally {
      setSaving(false);
    }
  }, [load]);

  const resetOverlay = useCallback(async (key: string) => {
    try {
      setSaving(true);
      setError(null);
      await resetRuntimeOverlay(key, 'Reset to Helm source');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset runtime overlay');
    } finally {
      setSaving(false);
    }
  }, [load]);

  if (loading) return <div className="text-center py-5"><Spinner animation="border" /></div>;

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="mb-1">Runtime Controls</h4>
          <p className="text-muted mb-0">Helm-sourced resources are locked. Runtime controls only add or remove group access overlays.</p>
        </div>
        <Button variant="outline-secondary" disabled={saving} onClick={load}>Refresh</Button>
      </div>
      {error && <Alert variant="danger" dismissible onClose={() => setError(null)}>{error}</Alert>}
      <div className="row g-3 mb-4">
        <SectionCard active={section === 'groups'} title="Groups" icon="bi-collection" count={groups.length} onClick={() => setSection('groups')} description="Lifecycle and effective resource access" />
        <SectionCard active={section === 'resources'} title="Resources" icon="bi-box-seam" count={resources.length} onClick={() => setSection('resources')} description="Helm-owned specs and access overlays" />
      </div>
      {section === 'groups' && (
        <Card>
          <Card.Header className="fw-semibold">Groups</Card.Header>
          <Card.Body>
            <Table responsive hover size="sm">
              <thead><tr><th>Group</th><th>Source</th><th>Effective resources</th><th>Lifecycle</th><th>Actions</th></tr></thead>
              <tbody>{groups.map(group => {
                const lifecycleOverlay = overlayFor(overlays, groupLifecycleKey(group.name));
                return <tr key={group.name}>
                  <td><strong>{group.name}</strong></td>
                  <td><Badge bg={group.source === 'helm' ? 'dark' : 'secondary'}>{group.source}</Badge></td>
                  <td><ResourceBadges resources={group.effectiveResources} /></td>
                  <td>{group.lifecycle.spawnSuspended ? <Badge bg="danger">Suspended</Badge> : <Badge bg="success">Open</Badge>}{lifecycleOverlay && <Badge bg="secondary" className="ms-1">overlay</Badge>}</td>
                  <td><Button size="sm" variant="outline-primary" onClick={() => setEditingGroup(group)}>Edit access</Button></td>
                </tr>;
              })}</tbody>
            </Table>
          </Card.Body>
        </Card>
      )}
      {section === 'resources' && (
        <Card>
          <Card.Header className="fw-semibold">Resources</Card.Header>
          <Card.Body>
            <Table responsive hover size="sm">
              <thead><tr><th>Resource</th><th>Source</th><th>Image/spec</th><th>Baseline groups</th><th>Overlay</th><th>Actions</th></tr></thead>
              <tbody>{resources.map(resource => {
                const accessOverlay = overlayFor(overlays, resourceAccessKey(resource.key));
                return <tr key={resource.key}>
                  <td><strong>{resource.metadata.description ?? resource.key}</strong><div className="text-muted small">{resource.key}</div></td>
                  <td><Badge bg="dark">{resource.source}</Badge></td>
                  <td><div className="small text-break">{resource.image}</div><div className="text-muted small">{resource.requirements.cpu} CPU / {resource.requirements.memory}</div></td>
                  <td><ResourceBadges resources={resource.baselineGroups} /></td>
                  <td>{accessOverlay ? <><Badge bg="info">add {resource.access.addGroups.length}</Badge><Badge bg="warning" text="dark" className="ms-1">deny {resource.access.denyGroups.length}</Badge></> : <span className="text-muted">None</span>}</td>
                  <td><Button size="sm" variant="outline-primary" onClick={() => setEditingResource(resource)}>Edit access</Button></td>
                </tr>;
              })}</tbody>
            </Table>
          </Card.Body>
        </Card>
      )}
      {editingGroup && <GroupAccessModal group={editingGroup} resources={resources} overlays={overlays} saving={saving} onHide={() => setEditingGroup(null)} onSaved={async () => { setEditingGroup(null); await load(); }} saveOverlay={saveOverlay} resetOverlay={resetOverlay} />}
      {editingResource && <ResourceAccessModal resource={editingResource} groups={groups} overlay={overlayFor(overlays, resourceAccessKey(editingResource.key))} saving={saving} onHide={() => setEditingResource(null)} onSaved={async () => { setEditingResource(null); await load(); }} saveOverlay={saveOverlay} resetOverlay={resetOverlay} />}
    </div>
  );
}

function SectionCard({ active, title, icon, count, description, onClick }: { active: boolean; title: string; icon: string; count: number; description: string; onClick: () => void }) {
  return <div className="col-md-6"><button type="button" className={`w-100 text-start bg-body border rounded-3 p-3 ${active ? 'border-primary shadow-sm' : ''}`} onClick={onClick}><div className="d-flex align-items-center gap-2 mb-2"><i className={`bi ${icon}`} /><strong>{title}</strong><Badge bg={active ? 'primary' : 'secondary'} className="ms-auto">{count}</Badge></div><div className="text-muted small">{description}</div></button></div>;
}

function ResourceBadges({ resources }: { resources: string[] }) {
  if (resources.length === 0) return <span className="text-muted">--</span>;
  return <div className="d-flex flex-wrap gap-1">{resources.map(resource => <Badge key={resource} bg="info">{resource}</Badge>)}</div>;
}

function GroupAccessModal({ group, resources, overlays, saving, onHide, onSaved, saveOverlay, resetOverlay }: { group: RuntimeControlsGroup; resources: RuntimeControlsResource[]; overlays: RuntimeOverlay[]; saving: boolean; onHide: () => void; onSaved: () => Promise<void>; saveOverlay: (key: string, value: Record<string, unknown>, reason: string, expectedRevision?: number) => Promise<void>; resetOverlay: (key: string) => Promise<void> }) {
  const [selected, setSelected] = useState(() => new Set(group.effectiveResources));
  const [lifecycle, setLifecycle] = useState<GroupLifecyclePolicy>(group.lifecycle);
  const [reason, setReason] = useState(group.lifecycle.reason || 'Update group access');
  const lifecycleOverlay = overlayFor(overlays, groupLifecycleKey(group.name));

  async function save() {
    await saveOverlay(groupLifecycleKey(group.name), lifecycle as unknown as Record<string, unknown>, reason, lifecycleOverlay?.revision);
    for (const resource of resources) {
      const baseline = group.baselineResources.includes(resource.key);
      const wanted = selected.has(resource.key);
      const access = resource.access;
      const next: ResourceAccessPolicy = {
        addGroups: wanted && !baseline ? Array.from(new Set([...access.addGroups, group.name])) : access.addGroups.filter(g => g !== group.name),
        denyGroups: !wanted && baseline ? Array.from(new Set([...access.denyGroups, group.name])) : access.denyGroups.filter(g => g !== group.name),
      };
      if (JSON.stringify(next) !== JSON.stringify(access)) {
        const key = resourceAccessKey(resource.key);
        await saveOverlay(key, next as unknown as Record<string, unknown>, `Update ${group.name} access`, overlayFor(overlays, key)?.revision);
      }
    }
    await onSaved();
  }

  return <Modal show onHide={onHide} size="lg"><Modal.Header closeButton><Modal.Title>Edit group access: {group.name}</Modal.Title></Modal.Header><Modal.Body><Alert variant="info">Helm baseline resources are locked. Changes below are stored as add/remove overlays.</Alert><Form.Check type="switch" label="Suspend new spawns for this group" checked={lifecycle.spawnSuspended} onChange={e => setLifecycle({ ...lifecycle, spawnSuspended: e.target.checked })} /><Form.Group className="mt-3"><Form.Label>Reason</Form.Label><Form.Control value={reason} onChange={e => { setReason(e.target.value); setLifecycle({ ...lifecycle, reason: e.target.value }); }} /></Form.Group><Form.Group className="mt-3"><Form.Label>Starts at</Form.Label><Form.Control type="datetime-local" value={(lifecycle.startsAt ?? '').slice(0, 16)} onChange={e => setLifecycle({ ...lifecycle, startsAt: e.target.value || null })} /></Form.Group><Form.Group className="mt-3"><Form.Label>Expires at</Form.Label><Form.Control type="datetime-local" value={(lifecycle.expiresAt ?? '').slice(0, 16)} onChange={e => setLifecycle({ ...lifecycle, expiresAt: e.target.value || null })} /></Form.Group><hr /><Form.Label className="fw-semibold">Effective resources</Form.Label><div className="row">{resources.map(resource => <div className="col-md-6" key={resource.key}><Form.Check checked={selected.has(resource.key)} label={`${resource.metadata.description ?? resource.key} (${resource.key})`} onChange={e => setSelected(prev => { const next = new Set(prev); if (e.target.checked) next.add(resource.key); else next.delete(resource.key); return next; })} /></div>)}</div></Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={saving || !lifecycleOverlay} onClick={() => resetOverlay(groupLifecycleKey(group.name))}>Reset lifecycle</Button><Button variant="secondary" disabled={saving} onClick={onHide}>Cancel</Button><Button variant="primary" disabled={saving} onClick={save}>Save overlays</Button></Modal.Footer></Modal>;
}

function ResourceAccessModal({ resource, groups, overlay, saving, onHide, onSaved, saveOverlay, resetOverlay }: { resource: RuntimeControlsResource; groups: RuntimeControlsGroup[]; overlay?: RuntimeOverlay; saving: boolean; onHide: () => void; onSaved: () => Promise<void>; saveOverlay: (key: string, value: Record<string, unknown>, reason: string, expectedRevision?: number) => Promise<void>; resetOverlay: (key: string) => Promise<void> }) {
  const [addGroups, setAddGroups] = useState(() => new Set(resource.access.addGroups));
  const [denyGroups, setDenyGroups] = useState(() => new Set(resource.access.denyGroups));
  const allGroups = groups.map(group => group.name);
  async function save() { await saveOverlay(resourceAccessKey(resource.key), { addGroups: [...addGroups], denyGroups: [...denyGroups] }, `Update ${resource.key} access`, overlay?.revision); await onSaved(); }
  return <Modal show onHide={onHide} size="lg"><Modal.Header closeButton><Modal.Title>Edit resource access: {resource.key}</Modal.Title></Modal.Header><Modal.Body><Alert variant="info">Resource image and runtime spec come from Helm and are locked here. This modal only changes which groups can access the resource.</Alert><h6>Additional groups</h6><div className="row mb-3">{allGroups.map(group => <div className="col-md-6" key={group}><Form.Check checked={addGroups.has(group)} label={group} onChange={e => setAddGroups(prev => { const next = new Set(prev); if (e.target.checked) next.add(group); else next.delete(group); return next; })} /></div>)}</div><h6>Denied baseline groups</h6><div className="row">{allGroups.map(group => <div className="col-md-6" key={group}><Form.Check checked={denyGroups.has(group)} label={group} onChange={e => setDenyGroups(prev => { const next = new Set(prev); if (e.target.checked) next.add(group); else next.delete(group); return next; })} /></div>)}</div></Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={saving || !overlay} onClick={() => resetOverlay(resourceAccessKey(resource.key))}>Reset overlay</Button><Button variant="secondary" disabled={saving} onClick={onHide}>Cancel</Button><Button variant="primary" disabled={saving} onClick={save}>Save overlay</Button></Modal.Footer></Modal>;
}
