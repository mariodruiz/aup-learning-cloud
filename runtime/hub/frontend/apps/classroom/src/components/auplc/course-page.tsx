import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { CourseTemplate, CourseUnit } from '@/lib/auplc/course-templates/types';
import { getAllCourseTemplates, buildUnitRequirement } from '@/lib/auplc/course-templates';
import { CourseCard, UnitCard } from './course-card';
import { nanoid } from 'nanoid';

const jhdata = window.jhdata ?? { base_url: '/hub/' };
const hubBase = jhdata.base_url ?? '/hub/';

interface ClassroomSummary {
  id: string;
  name: string;
  description?: string;
  sceneCount: number;
  createdAt: string;
  meta?: { courseKey?: string; unitId?: string };
}

export function CoursePage() {
  const navigate = useNavigate();
  const [selectedCourse, setSelectedCourse] = useState<CourseTemplate | null>(null);
  const [savedClassrooms, setSavedClassrooms] = useState<ClassroomSummary[]>([]);
  const templates = getAllCourseTemplates();

  useEffect(() => {
    fetch('/api/classroom?list=1')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.success && data.classrooms) {
          setSavedClassrooms(data.classrooms);
        }
      })
      .catch(() => {});
  }, []);

  const getSavedClassroom = (courseKey: string, unitId: string): ClassroomSummary | undefined =>
    savedClassrooms.find((c) => c.meta?.courseKey === courseKey && c.meta?.unitId === unitId);

  const handleStartAI = (template: CourseTemplate, unit: CourseUnit) => {
    const requirement = buildUnitRequirement(template, unit.id);
    const sessionState = {
      sessionId: nanoid(),
      requirements: { requirement, language: template.language },
      pdfText: '',
      pdfImages: [],
      imageStorageIds: [],
      sceneOutlines: null,
      currentStep: 'generating' as const,
      courseKey: template.courseKey,
      unitId: unit.id,
    };
    sessionStorage.setItem('generationSession', JSON.stringify(sessionState));
    navigate('/generation-preview');
  };

  const handleEnterClassroom = (classroomId: string) => {
    navigate(`/classroom/${classroomId}`);
  };

  const handleLaunchLab = (template: CourseTemplate, _unit: CourseUnit) => {
    window.location.href = `${hubBase}spawn?resource=${encodeURIComponent(template.courseKey)}`;
  };

  if (!selectedCourse) {
    return (
      <>
        <div className="home-section-header">
          <h2>AI-Guided Courses</h2>
        </div>
        <div className="resources-grid">
          {templates.map((t) => (
            <CourseCard key={t.courseKey} template={t} onSelect={setSelectedCourse} />
          ))}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="home-section-header">
        <h2>
          <a onClick={() => setSelectedCourse(null)} style={{ cursor: 'pointer', textDecoration: 'none', color: 'var(--home-primary)' }}>
            <i className="fa fa-arrow-left" style={{ fontSize: '0.7rem', marginRight: '0.5rem' }}></i>
          </a>
          {selectedCourse.name}
        </h2>
        <span style={{ fontSize: '0.78rem', color: 'var(--home-text-muted)' }}>
          {selectedCourse.units.length} learning units
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {selectedCourse.units.map((unit) => {
          const saved = getSavedClassroom(selectedCourse.courseKey, unit.id);
          return (
            <UnitCard
              key={unit.id}
              unit={unit}
              courseKey={selectedCourse.courseKey}
              savedClassroomId={saved?.id}
              savedAt={saved?.createdAt}
              onStartAI={(u) => handleStartAI(selectedCourse, u)}
              onEnterClassroom={handleEnterClassroom}
              onLaunchLab={(u) => handleLaunchLab(selectedCourse, u)}
            />
          );
        })}
      </div>
    </>
  );
}
