const taskTemplates = {
  search: "Search the web about: ",
  summarize: "Summarize the following text: ",
  system: "Run the following system command (local only): ",
  memory: "Save this in memory: ",
  rag: "Answer using RAG: "
};

export default function TaskMenu({ onSelect }) {
  const tasks = [
    { id: "search", label: "Web Search" },
    { id: "summarize", label: "Summarize Text" },
    { id: "system", label: "Run Command" },
    { id: "memory", label: "Store Memory" },
    { id: "rag", label: "Ask RAG DB" }
  ];

  return (
    <div className="task-menu">
      <h3>Tasks</h3>
      <ul>
        {tasks.map((task) => (
          <li key={task.id}>
            <button onClick={() => onSelect(task.id, taskTemplates[task.id])}>
              {task.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
