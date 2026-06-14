# NeumoContent MX

Generador de contenido médico para redes sociales — neumólogo mexicano.
React + TypeScript + Vite + Tailwind CSS.

## Configuración de API keys

Copia `.env.local.example` a `.env.local` y agrega tus claves:

```
VITE_ANTHROPIC_KEY=sk-ant-...
VITE_GEMINI_KEY=AIzaSy...
VITE_OPENAI_KEY=sk-proj-...
```

> **Nota de seguridad:** Esta app llama a las APIs de IA directamente desde el
> navegador usando las keys en `.env.local`. Esto es aceptable para uso personal
> local. Si se despliega en Vercel para uso propio, las keys quedan expuestas en
> el bundle del cliente — es un riesgo aceptado para v1 de un solo usuario, pero
> **NO compartir la URL de producción con terceros** sin antes mover las llamadas
> a un backend proxy (Fase futura).

## Desarrollo

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Estructura

```
src/
  lib/ai/          # Cliente IA (Claude/Gemini/ChatGPT), prompts, parser
  lib/compliance/  # Checker normativo NOM-004/COFEPRIS
  lib/imageGen/    # Fase 3: generación de imagen
  lib/share/       # Fase 3: copiar y publicar asistido
  data/            # Topics, posts, hashtags, datos del médico
  features/        # Vistas: Dashboard, Topics, Generator, etc.
  types/           # Tipos TypeScript compartidos
```
