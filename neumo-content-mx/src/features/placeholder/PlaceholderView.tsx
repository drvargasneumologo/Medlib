interface Props {
  title: string;
  description: string;
  icon: string;
}

export default function PlaceholderView({ title, description, icon }: Props) {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">{title}</h1>
      <p className="text-gray-500 mb-8">{description}</p>
      <div className="flex flex-col items-center justify-center py-24 text-gray-300">
        <span className="text-6xl mb-4">{icon}</span>
        <p className="text-sm">Próximamente — Fase 2</p>
      </div>
    </div>
  );
}
