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
import type { GroupLifecyclePolicy, ResourceAccessPolicy, ResourceRequirements, RuntimeControlsGroup, RuntimeControlsResource, RuntimeOverlay } from '@auplc/shared';
import { deleteRuntimeResource, getRuntimeControls, resetRuntimeOverlay, saveRuntimeResource, setRuntimeOverlay } from '@auplc/shared';

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
  const [editingResourceSpec, setEditingResourceSpec] = useState<RuntimeControlsResource | null>(null);
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

  const saveOverlay = useCallback(async (key: string, value: Record<string, unknown>, expectedRevision?: number) => {
    try {
      setSaving(true);
      setError(null);
      await setRuntimeOverlay(key, value, expectedRevision);
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
      await resetRuntimeOverlay(key);
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
          <p className="text-muted mb-0">Helm-sourced resources are locked; database resources can be managed here and layered with access overlays.</p>
        </div>
        <Button variant="outline-secondary" disabled={saving} onClick={load}>Refresh</Button>
      </div>
      {error && <Alert variant="danger" dismissible onClose={() => setError(null)}>{error}</Alert>}
      <div className="row g-3 mb-4">
        <SectionCard active={section === 'groups'} title="Groups" icon="bi-collection" count={groups.length} onClick={() => setSection('groups')} description="Lifecycle and effective resource access" />
        <SectionCard active={section === 'resources'} title="Resources" icon="bi-box-seam" count={resources.length} onClick={() => setSection('resources')} description="Locked Helm specs and editable DB resources" />
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
          <Card.Header className="d-flex align-items-center justify-content-between">
            <span className="fw-semibold">Resources</span>
            <Button
              size="sm"
              variant="primary"
              onClick={() => setEditingResourceSpec({
                key: '',
                source: 'database',
                image: '',
                requirements: { cpu: '2', memory: '4Gi' },
                metadata: { group: 'OTHERS', description: '', subDescription: '', acceleratorKeys: [], allowGitClone: false },
                access: { addGroups: [], denyGroups: [] },
                baselineGroups: [],
                enabled: true,
                locked: false,
              })}
            >
              New database resource
            </Button>
          </Card.Header>
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
                  <td className="d-flex flex-wrap gap-2">
                    <Button size="sm" variant="outline-primary" onClick={() => setEditingResource(resource)}>Edit access</Button>
                    <Button size="sm" variant="outline-secondary" disabled={resource.source === 'helm'} onClick={() => setEditingResourceSpec(resource)}>Edit spec</Button>
                    <Button size="sm" variant="outline-danger" disabled={resource.source === 'helm'} onClick={async () => {
                      if (!window.confirm(`Delete database resource '${resource.key}'?`)) return;
                      setSaving(true);
                      try {
                        await deleteRuntimeResource(resource.key);
                        await load();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : 'Failed to delete database resource');
                      } finally {
                        setSaving(false);
                      }
                    }}>Delete</Button>
                  </td>
                </tr>;
              })}</tbody>
            </Table>
          </Card.Body>
        </Card>
      )}
      {editingGroup && <GroupAccessModal group={editingGroup} resources={resources} overlays={overlays} saving={saving} onHide={() => setEditingGroup(null)} onSaved={async () => { setEditingGroup(null); await load(); }} saveOverlay={saveOverlay} resetOverlay={resetOverlay} />}
      {editingResource && <ResourceAccessModal resource={editingResource} groups={groups} overlay={overlayFor(overlays, resourceAccessKey(editingResource.key))} saving={saving} onHide={() => setEditingResource(null)} onSaved={async () => { setEditingResource(null); await load(); }} saveOverlay={saveOverlay} resetOverlay={resetOverlay} />}
      {editingResourceSpec && <ResourceSpecModal resource={editingResourceSpec} saving={saving} onHide={() => setEditingResourceSpec(null)} onSaved={async () => { setEditingResourceSpec(null); await load(); }} />}
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

function GroupAccessModal({ group, resources, overlays, saving, onHide, onSaved, saveOverlay, resetOverlay }: { group: RuntimeControlsGroup; resources: RuntimeControlsResource[]; overlays: RuntimeOverlay[]; saving: boolean; onHide: () => void; onSaved: () => Promise<void>; saveOverlay: (key: string, value: Record<string, unknown>, expectedRevision?: number) => Promise<void>; resetOverlay: (key: string) => Promise<void> }) {
  const [selected, setSelected] = useState(() => new Set(group.effectiveResources));
  const [lifecycle, setLifecycle] = useState<GroupLifecyclePolicy>(group.lifecycle);
  const lifecycleOverlay = overlayFor(overlays, groupLifecycleKey(group.name));

  async function save() {
    await saveOverlay(groupLifecycleKey(group.name), lifecycle as unknown as Record<string, unknown>, lifecycleOverlay?.revision);
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
        await saveOverlay(key, next as unknown as Record<string, unknown>, overlayFor(overlays, key)?.revision);
      }
    }
    await onSaved();
  }

  return <Modal show onHide={onHide} size="lg"><Modal.Header closeButton><Modal.Title>Edit group access: {group.name}</Modal.Title></Modal.Header><Modal.Body><Alert variant="info">Helm baseline resources are locked. Changes below are stored as add/remove overlays.</Alert><Form.Check type="switch" label="Suspend new spawns for this group" checked={lifecycle.spawnSuspended} onChange={e => setLifecycle({ ...lifecycle, spawnSuspended: e.target.checked })} /><Form.Group className="mt-3"><Form.Label>Starts at</Form.Label><Form.Control type="datetime-local" value={(lifecycle.startsAt ?? '').slice(0, 16)} onChange={e => setLifecycle({ ...lifecycle, startsAt: e.target.value || null })} /></Form.Group><Form.Group className="mt-3"><Form.Label>Expires at</Form.Label><Form.Control type="datetime-local" value={(lifecycle.expiresAt ?? '').slice(0, 16)} onChange={e => setLifecycle({ ...lifecycle, expiresAt: e.target.value || null })} /></Form.Group><hr /><Form.Label className="fw-semibold">Effective resources</Form.Label><div className="row">{resources.map(resource => <div className="col-md-6" key={resource.key}><Form.Check checked={selected.has(resource.key)} label={`${resource.metadata.description ?? resource.key} (${resource.key})`} onChange={e => setSelected(prev => { const next = new Set(prev); if (e.target.checked) next.add(resource.key); else next.delete(resource.key); return next; })} /></div>)}</div></Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={saving || !lifecycleOverlay} onClick={() => resetOverlay(groupLifecycleKey(group.name))}>Reset lifecycle</Button><Button variant="secondary" disabled={saving} onClick={onHide}>Cancel</Button><Button variant="primary" disabled={saving} onClick={save}>Save overlays</Button></Modal.Footer></Modal>;
}

function ResourceAccessModal({ resource, groups, overlay, saving, onHide, onSaved, saveOverlay, resetOverlay }: { resource: RuntimeControlsResource; groups: RuntimeControlsGroup[]; overlay?: RuntimeOverlay; saving: boolean; onHide: () => void; onSaved: () => Promise<void>; saveOverlay: (key: string, value: Record<string, unknown>, expectedRevision?: number) => Promise<void>; resetOverlay: (key: string) => Promise<void> }) {
  const [addGroups, setAddGroups] = useState(() => new Set(resource.access.addGroups));
  const [denyGroups, setDenyGroups] = useState(() => new Set(resource.access.denyGroups));
  const allGroups = groups.map(group => group.name);
  async function save() { await saveOverlay(resourceAccessKey(resource.key), { addGroups: [...addGroups], denyGroups: [...denyGroups] }, overlay?.revision); await onSaved(); }
  return <Modal show onHide={onHide} size="lg"><Modal.Header closeButton><Modal.Title>Edit resource access: {resource.key}</Modal.Title></Modal.Header><Modal.Body><Alert variant="info">This modal changes which groups can access the resource. Helm resource specs stay locked; database resource specs are edited separately.</Alert><h6>Additional groups</h6><div className="row mb-3">{allGroups.map(group => <div className="col-md-6" key={group}><Form.Check checked={addGroups.has(group)} label={group} onChange={e => setAddGroups(prev => { const next = new Set(prev); if (e.target.checked) next.add(group); else next.delete(group); return next; })} /></div>)}</div><h6>Denied baseline groups</h6><div className="row">{allGroups.map(group => <div className="col-md-6" key={group}><Form.Check checked={denyGroups.has(group)} label={group} onChange={e => setDenyGroups(prev => { const next = new Set(prev); if (e.target.checked) next.add(group); else next.delete(group); return next; })} /></div>)}</div></Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={saving || !overlay} onClick={() => resetOverlay(resourceAccessKey(resource.key))}>Reset overlay</Button><Button variant="secondary" disabled={saving} onClick={onHide}>Cancel</Button><Button variant="primary" disabled={saving} onClick={save}>Save overlay</Button></Modal.Footer></Modal>;
}

function ResourceSpecModal({ resource, saving, onHide, onSaved }: { resource: RuntimeControlsResource; saving: boolean; onHide: () => void; onSaved: () => Promise<void> }) {
  const [key, setKey] = useState(resource.key);
  const [image, setImage] = useState(resource.image);
  const [cpu, setCpu] = useState(resource.requirements.cpu);
  const [memory, setMemory] = useState(resource.requirements.memory);
  const [memoryLimit, setMemoryLimit] = useState(resource.requirements.memory_limit ?? '');
  const [gpu, setGpu] = useState(resource.requirements['amd.com/gpu'] ?? '');
  const [npu, setNpu] = useState(resource.requirements['amd.com/npu'] ?? '');
  const [group, setGroup] = useState(resource.metadata.group ?? 'OTHERS');
  const [description, setDescription] = useState(resource.metadata.description ?? '');
  const [subDescription, setSubDescription] = useState(resource.metadata.subDescription ?? '');
  const [accelerator, setAccelerator] = useState(resource.metadata.accelerator ?? '');
  const [acceleratorKeys, setAcceleratorKeys] = useState((resource.metadata.acceleratorKeys ?? []).join(', '));
  const [allowGitClone, setAllowGitClone] = useState(Boolean(resource.metadata.allowGitClone));
  const [enabled, setEnabled] = useState(resource.enabled ?? true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [localSaving, setLocalSaving] = useState(false);
  const busy = saving || localSaving;

  async function save() {
    try {
      setLocalSaving(true);
      setLocalError(null);
      const requirements: ResourceRequirements = { cpu, memory };
      if (memoryLimit) requirements.memory_limit = memoryLimit;
      if (gpu) requirements['amd.com/gpu'] = gpu;
      if (npu) requirements['amd.com/npu'] = npu;
      await saveRuntimeResource({
        ...resource,
        key,
        source: 'database',
        image,
        requirements,
        enabled,
        metadata: {
          group,
          description,
          subDescription,
          accelerator,
          acceleratorKeys: acceleratorKeys.split(',').map(value => value.trim()).filter(Boolean),
          allowGitClone,
        },
      });
      await onSaved();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to save database resource');
    } finally {
      setLocalSaving(false);
    }
  }

  return <Modal show onHide={onHide} size="lg">
    <Modal.Header closeButton>
      <Modal.Title>{resource.key ? 'Edit' : 'Create'} database resource</Modal.Title>
    </Modal.Header>
    <Modal.Body>
      {localError && <Alert variant="danger" dismissible onClose={() => setLocalError(null)}>{localError}</Alert>}
      <Alert variant="info">Database resources are editable. Helm-provisioned resources remain locked and cannot be changed here.</Alert>
      <Form.Group className="mb-3">
        <Form.Label>Resource key</Form.Label>
        <Form.Control value={key} disabled={Boolean(resource.key)} onChange={e => setKey(e.target.value)} />
      </Form.Group>
      <Form.Group className="mb-3">
        <Form.Label>Image</Form.Label>
        <Form.Control value={image} onChange={e => setImage(e.target.value)} />
      </Form.Group>
      <div className="row">
        <Form.Group className="col-md-4 mb-3">
          <Form.Label>CPU</Form.Label>
          <Form.Control value={cpu} onChange={e => setCpu(e.target.value)} />
        </Form.Group>
        <Form.Group className="col-md-4 mb-3">
          <Form.Label>Memory</Form.Label>
          <Form.Control value={memory} onChange={e => setMemory(e.target.value)} />
        </Form.Group>
        <Form.Group className="col-md-4 mb-3">
          <Form.Label>Memory limit</Form.Label>
          <Form.Control value={memoryLimit} placeholder="Optional" onChange={e => setMemoryLimit(e.target.value)} />
        </Form.Group>
      </div>
      <div className="row">
        <Form.Group className="col-md-6 mb-3">
          <Form.Label>GPU request</Form.Label>
          <Form.Control value={gpu} placeholder="Optional" onChange={e => setGpu(e.target.value)} />
        </Form.Group>
        <Form.Group className="col-md-6 mb-3">
          <Form.Label>NPU request</Form.Label>
          <Form.Control value={npu} placeholder="Optional" onChange={e => setNpu(e.target.value)} />
        </Form.Group>
      </div>
      <Form.Group className="mb-3">
        <Form.Label>UI group/category</Form.Label>
        <Form.Control value={group} onChange={e => setGroup(e.target.value)} />
      </Form.Group>
      <Form.Group className="mb-3">
        <Form.Label>Description</Form.Label>
        <Form.Control value={description} onChange={e => setDescription(e.target.value)} />
      </Form.Group>
      <Form.Group className="mb-3">
        <Form.Label>Sub-description</Form.Label>
        <Form.Control value={subDescription} onChange={e => setSubDescription(e.target.value)} />
      </Form.Group>
      <Form.Group className="mb-3">
        <Form.Label>Accelerator label</Form.Label>
        <Form.Control value={accelerator} onChange={e => setAccelerator(e.target.value)} />
      </Form.Group>
      <Form.Group className="mb-3">
        <Form.Label>Accelerator keys</Form.Label>
        <Form.Control value={acceleratorKeys} placeholder="Comma-separated accelerator keys" onChange={e => setAcceleratorKeys(e.target.value)} />
      </Form.Group>
      <Form.Check className="mb-3" checked={allowGitClone} label="Allow Git clone" onChange={e => setAllowGitClone(e.target.checked)} />
      <Form.Check className="mb-3" checked={enabled} label="Enabled" onChange={e => setEnabled(e.target.checked)} />
    </Modal.Body>
    <Modal.Footer>
      <Button variant="secondary" disabled={busy} onClick={onHide}>Cancel</Button>
      <Button variant="primary" disabled={busy} onClick={save}>Save resource</Button>
    </Modal.Footer>
  </Modal>;
}
