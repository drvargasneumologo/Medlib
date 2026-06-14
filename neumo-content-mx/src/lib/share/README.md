# lib/share

Fase 3: "copiar y publicar asistido". Copia el caption + hashtags +
disclaimer al portapapeles y abre un deep link a la red social
correspondiente (Instagram, Facebook, LinkedIn, Twitter/X) para que el
médico pegue y publique manualmente.

DECISIÓN DE ARQUITECTURA — NO CAMBIAR sin reevaluar:
No se integra directamente con Meta Graph API ni Twitter API v2 en este
proyecto. Meta requiere App Review + Verificación de Negocio (4-8 semanas).
Twitter/X cobra por publicación vía API (~$0.20 USD/post con URL).
Si en el futuro se justifica automatización completa por volumen de uso
diario, evaluar un API unificado de pago (Ayrshare/Blotato) que ya pasó
el proceso de revisión — Fase 4 opcional.
