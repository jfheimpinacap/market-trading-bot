const plannedModules = [
  'Frontend web dashboard',
  'Backend API and orchestration',
  'Provider adapters for market venues',
  'Discovery, probability, risk, and execution engines',
  'Post-mortem workflows and research documentation',
];

export function ModuleList() {
  return (
    <section className="card">
      <h2>Planned modules</h2>
      <ul className="module-list">
        {plannedModules.map((moduleName) => (
          <li key={moduleName}>{moduleName}</li>
        ))}
      </ul>
    </section>
  );
}
