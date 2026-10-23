# Atalhos. Uso: make episodio SLUG=ep-02-o-segundo-sino
SLUG ?= ep-01-o-reino-que-esqueceu-o-sol
PY ?= python3

.PHONY: help instalar novo roteiro narrar imagens timeline render preview pacote publicar demo testes limpar

help:
	@echo "make instalar                     instala as dependências"
	@echo "make novo SLUG=ep-02 TITULO='...' NUMERO=2"
	@echo "make roteiro|narrar|imagens|timeline|render|preview|pacote SLUG=..."
	@echo "make episodio SLUG=...            pipeline completo (sem publicar)"
	@echo "make publicar SLUG=...            envia e agenda no YouTube"
	@echo "make demo                         render de 3 cenas em 720p (sem voz)"
	@echo "make testes                       roda a suíte"

instalar:
	$(PY) -m pip install -r requirements.txt

novo:
	$(PY) -m fabrica novo $(SLUG) --titulo "$(TITULO)" --numero $(NUMERO)

roteiro narrar imagens timeline preview pacote:
	$(PY) -m fabrica $@ $(SLUG)

render:
	$(PY) -m fabrica render $(SLUG)

episodio:
	$(PY) -m fabrica roteiro $(SLUG)
	$(PY) -m fabrica narrar  $(SLUG)
	$(PY) -m fabrica imagens $(SLUG)
	$(PY) -m fabrica timeline $(SLUG)
	$(PY) -m fabrica render  $(SLUG)
	$(PY) -m fabrica pacote  $(SLUG)
	$(PY) -m fabrica preview $(SLUG)

publicar:
	$(PY) -m fabrica publicar $(SLUG) --agendar

demo:
	$(PY) -m fabrica render $(SLUG) --preview --limite 3
	$(PY) -m fabrica preview $(SLUG)

testes:
	$(PY) -m unittest discover -s tests -v

limpar:
	rm -rf episodes/*/build episodes/*/shots episodes/*/trilha episodes/*/narracao
