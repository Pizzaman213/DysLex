import { useErrorProfile } from '../../hooks/useErrorProfile';

export function ProgressDashboard() {
  const { profile, isLoading } = useErrorProfile();

  if (isLoading) {
    return (
      <div className="progress-dashboard" role="region" aria-label="Progress dashboard">
        <h2>Your Progress</h2>
        <p>Loading your progress...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="progress-dashboard" role="region" aria-label="Progress dashboard">
        <h2>Your Progress</h2>
        <p>Start writing to see your progress!</p>
      </div>
    );
  }

  return (
    <div className="progress-dashboard" role="region" aria-label="Progress dashboard">
      <h2>Your Progress</h2>

      <div className="progress-section">
        <h3>Writing Strength</h3>
        <div className="strength-meter" role="meter" aria-valuenow={profile.overallScore} aria-valuemin={0} aria-valuemax={100}>
          <div className="strength-fill" style={{ width: `${profile.overallScore}%` }} />
        </div>
        <p className="strength-label">{getStrengthLabel(profile.overallScore)}</p>
      </div>

      <div className="progress-section">
        <h3>Patterns Learned</h3>
        <ul className="patterns-list">
          {profile.topPatterns.map((pattern) => (
            <li key={pattern.id} className="pattern-item">
              <span className="pattern-name">{pattern.description}</span>
              <span className="pattern-progress">
                {pattern.mastered ? '✓ Mastered' : `${pattern.progress}%`}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="progress-section">
        <h3>Recent Achievements</h3>
        <ul className="achievements-list">
          {profile.achievements.slice(0, 3).map((achievement) => (
            <li key={achievement.id} className="achievement-item">
              <span className="achievement-icon" aria-hidden="true">{achievement.icon}</span>
              <span className="achievement-name">{achievement.name}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function getStrengthLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Strong';
  if (score >= 40) return 'Growing';
  if (score >= 20) return 'Learning';
  return 'Getting Started';
}
