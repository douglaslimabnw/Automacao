# Checklist de publicação (10 minutos)

## Antes de renderizar

- [ ] `python -m fabrica roteiro <slug>` sem avisos de duração
- [ ] `python -m fabrica timeline <slug>` → 10–15 min, narração ≥ 85% do vídeo
- [ ] nenhuma cena repetida com a mesma arte em sequência
- [ ] gancho de meio existe e soa como parte da história
- [ ] fecho promete algo concreto

## Depois de renderizar

- [ ] assistir aos 60 primeiros segundos sem pular
- [ ] conferir se a legenda não cobre o rosto/personagem
- [ ] áudio: voz sempre acima da trilha (o ducking faz isso, mas confira no celular)
- [ ] `ffmpeg -i final.mp4` → 1920×1080, 24 fps, aac 48 kHz

## Pacote

- [ ] thumbnail 1280×720 legível em miniatura (teste diminuindo para 160 px)
- [ ] título com no máximo 60 caracteres visíveis
- [ ] descrição com capítulos (a fábrica gera em `plan.json`)
- [ ] `legendas.srt` enviado (SEO + acessibilidade)
- [ ] `publicar --agendar --dry-run` revisado

## Depois de publicar

- [ ] fixar um comentário com a pergunta que o vídeo deixa aberta
- [ ] responder os 10 primeiros comentários na primeira hora
- [ ] anotar no `docs/BIBLIA.md` o que foi revelado (para não contradizer depois)
- [ ] escrever o roteiro do próximo episódio **antes** de olhar as métricas
