import type { CourseTemplate, CourseUnit } from '@/lib/auplc/course-templates/types';

interface CourseCardProps {
  template: CourseTemplate;
  onSelect: (template: CourseTemplate) => void;
}

export function CourseCard({ template, onSelect }: CourseCardProps) {
  return (
    <a className="resource-card" onClick={() => onSelect(template)} style={{ cursor: 'pointer' }}>
      <div className="resource-card-top">
        <div className="resource-card-info">
          <h4>{template.name}</h4>
          <p>{template.description}</p>
        </div>
        <span className="resource-card-arrow"><i className="fa fa-arrow-right"></i></span>
      </div>
      <div className="resource-card-tags">
        <span className="resource-tag tag-gpu">GPU</span>
        <span className="resource-tag tag-spec">{template.units.length} AI-guided labs</span>
        <span className="resource-tag tag-git"><i className="fa fa-magic" style={{ fontSize: '0.55rem' }}></i> AI</span>
      </div>
    </a>
  );
}

interface UnitCardProps {
  unit: CourseUnit;
  courseKey: string;
  savedClassroomId?: string;
  savedAt?: string;
  onStartAI: (unit: CourseUnit) => void;
  onEnterClassroom: (classroomId: string) => void;
  onLaunchLab: (unit: CourseUnit) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function UnitCard({ unit, savedClassroomId, savedAt, onStartAI, onEnterClassroom, onLaunchLab }: UnitCardProps) {
  return (
    <div className="resource-card" style={{ flexDirection: 'row', alignItems: 'center', gap: '1rem', cursor: 'default' }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: savedClassroomId ? '#10b981' : 'var(--home-primary)', color: '#fff',
        fontSize: '0.72rem', fontWeight: 700, flexShrink: 0
      }}>
        {savedClassroomId ? <i className="fa fa-check" style={{ fontSize: '0.7rem' }}></i> : unit.order}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--home-text)', margin: 0 }}>{unit.title}</h4>
        <p style={{ fontSize: '0.72rem', color: 'var(--home-text-secondary)', margin: '2px 0 0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {savedClassroomId && savedAt
            ? `Generated ${formatDate(savedAt)} — ${unit.description}`
            : unit.description}
        </p>
      </div>
      <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
        {savedClassroomId ? (
          <>
            <a role="button" className="btn-launch" onClick={() => onEnterClassroom(savedClassroomId)} style={{ fontSize: '0.75rem', padding: '0.4rem 0.9rem' }}>
              <i className="fa fa-graduation-cap"></i> Enter
            </a>
            <a role="button" className="btn-home-sm" onClick={() => onStartAI(unit)} style={{ fontSize: '0.75rem' }} title="Regenerate">
              <i className="fa fa-refresh"></i>
            </a>
          </>
        ) : (
          <a role="button" className="btn-launch" onClick={() => onStartAI(unit)} style={{ fontSize: '0.75rem', padding: '0.4rem 0.9rem' }}>
            <i className="fa fa-magic"></i> AI Learn
          </a>
        )}
        <a role="button" className="btn-home-sm" onClick={() => onLaunchLab(unit)} style={{ fontSize: '0.75rem' }}>
          <i className="fa fa-terminal"></i> Lab
        </a>
      </div>
    </div>
  );
}
