"""Testes de ponta a ponta da fábrica (rodam offline, em ~1 min).

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

from fabrica import audio_gen, arte, imagens, render, roteiro, subtitles, timeline  # noqa: E402
from fabrica.config import Episodio  # noqa: E402
from fabrica.util import duracao, salvar_json, tempo  # noqa: E402

ROTEIRO_TESTE = """\
# Episódio 99 — Teste da Fábrica

## Cena 1 — Abertura

Eu desci os degraus contando. Na décima segunda, o sino tocou sozinho.

> GANCHO

Se isso te prendeu, deixa o like.

## Cena 2 — A sala
visual: trono

Eu vi trinta sinos. Nenhum tinha badalo.

> PROXIMO

Semana que vem eu mostro o que tem embaixo.
"""


class TestRoteiro(unittest.TestCase):
    def test_le_cenas_e_marcas(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "roteiro.md"
            p.write_text(ROTEIRO_TESTE, encoding="utf-8")
            cenas = roteiro.ler_roteiro(p)
        self.assertEqual(len(cenas), 2)
        self.assertEqual(cenas[0]["marca"], "gancho")
        self.assertEqual(cenas[1]["marca"], "proximo")
        self.assertEqual(cenas[1]["visual"], "trono")
        self.assertNotIn("GANCHO", cenas[0]["texto"])

    def test_plano_tem_abertura_gancho_e_fecho(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "roteiro.md"
            p.write_text(ROTEIRO_TESTE, encoding="utf-8")
            cenas = roteiro.ler_roteiro(p)
        plan = roteiro.construir_plan("ep-teste", "vozes-do-abismo", "Teste", 99, cenas)
        tipos = [c["tipo"] for c in plan["cenas"]]
        self.assertEqual(tipos[0], "cartao")
        self.assertEqual(tipos[-1], "cta")
        self.assertIn("gancho", tipos)
        self.assertIn("proximo", tipos)
        ids = [c["id"] for c in plan["cenas"]]
        self.assertEqual(len(ids), len(set(ids)), "ids duplicados")

    def test_divisao_em_planos_limita_tamanho(self):
        texto = " ".join(["Eu vi o sino tocar."] * 40)
        pedacos = roteiro._dividir(texto)
        self.assertGreater(len(pedacos), 1)
        self.assertTrue(all(len(p.split()) <= 60 for p in pedacos))

    def test_visual_inferido_do_texto(self):
        self.assertEqual(roteiro.inferir_arquetipo("a floresta estava quieta"), "floresta")
        self.assertEqual(roteiro.inferir_arquetipo("o trono do rei"), "trono")
        self.assertEqual(roteiro.inferir_arquetipo("nada relevante"), "abismo")

    def test_limpa_marcas(self):
        self.assertEqual(roteiro.limpar_marcas("oi [pausa] tudo bem"), "oi  tudo bem")


class TestTimeline(unittest.TestCase):
    def test_estimativa_de_duracao(self):
        self.assertGreater(timeline.duracao_estimada("uma frase curta aqui"), 1.5)
        self.assertEqual(timeline.duracao_estimada(""), 0.0)

    def test_tempo_formata_srt(self):
        self.assertEqual(tempo(3661.5), "01:01:01.500")

    def test_ordem_visual_nao_repete(self):
        cenas = [{"id": str(i)} for i in range(6)]
        for a, b in zip(timeline.ordem_visual(cenas, 7), timeline.ordem_visual(cenas, 7)[1:]):
            self.assertNotEqual(a["movimento"], b["movimento"])


class TestLegendas(unittest.TestCase):
    def test_cues_e_srt(self):
        tl = {"eventos": [{"id": "c1", "inicio": 0.0, "duracao": 4.0, "fim": 4.0,
                           "narracao": "Uma frase. Outra frase mais longa aqui. E mais uma.",
                           "tipo": "fala", "legenda": None}]}
        lista = subtitles.cues(tl)
        self.assertGreater(len(lista), 1)
        self.assertTrue(all(c["fim"] > c["inicio"] for c in lista))
        with tempfile.TemporaryDirectory() as tmp:
            srt = subtitles.escrever_srt(Path(tmp) / "a.srt", lista)
            texto = srt.read_text(encoding="utf-8")
            self.assertIn("-->", texto)
            ass = subtitles.escrever_ass(Path(tmp) / "a.ass", lista)
            conteudo = ass.read_text(encoding="utf-8")
            self.assertIn("Bebas Neue", conteudo)
            self.assertIn("Dialogue:", conteudo)


class TestAudio(unittest.TestCase):
    def test_trilha_e_sfx(self):
        bed = audio_gen.trilha(3.0, mood="melancolico", semente=1, intensidade=0.3)
        self.assertEqual(bed.shape, (3 * 48000, 2))
        self.assertLessEqual(float(np.abs(bed).max()), 1.0)
        for f in (audio_gen.whoosh, audio_gen.impacto, audio_gen.riser):
            self.assertGreater(f().size, 1000)


class TestArte(unittest.TestCase):
    def test_cenarios_geram_imagem_valida(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, arq in enumerate(arte.ARQUETIPOS):
                p = arte.gerar(arq, 100 + i, Path(tmp) / f"{arq}.jpg",
                               largura=480, altura=270, figura=i % 2 == 0)
                self.assertTrue(p.exists())
                self.assertGreater(p.stat().st_size, 4000)

    def test_cartao_e_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = arte.cartao_titulo("Título", "Episódio 01", Path(tmp) / "c.jpg", 5,
                                   largura=640, altura=360)
            self.assertTrue(c.exists())
            th = arte.thumbnail(c, "TITULO", Path(tmp) / "t.jpg", linha2="sub")
            from PIL import Image
            with Image.open(th) as im:
                self.assertEqual(im.size, (1280, 720))


class TestRenderPontaAPonta(unittest.TestCase):
    """Renderiza 2 cenas curtas com voz sintética e valida o MP4."""

    def test_episodio_minimo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "episodes" / "ep-teste"
            base.mkdir(parents=True)
            shutil.copytree(RAIZ / "series", Path(tmp) / "series")
            (base / "roteiro.md").write_text(ROTEIRO_TESTE, encoding="utf-8")
            salvar_json(base / "ep.json", {"serie": "vozes-do-abismo", "titulo": "Teste",
                                           "numero": 99, "ganchos": True, "semente": 5})
            # a fábrica resolve caminhos a partir de RAIZ; apontamos para o tmp
            import fabrica.config as config
            import fabrica.util as util
            originais = {m: m.RAIZ for m in (util, config, roteiro)}
            for m in originais:
                m.RAIZ = Path(tmp)
            try:
                roteiro.gerar_roteiro("ep-teste", forcar=True)
                ep = Episodio("ep-teste")
                ep.garantir_pastas()
                # voz: provedor "silencio" evita rede
                from fabrica import voz
                voz.narrar(ep, provedor="silencio")
                imagens.planejar_imagens(ep, largura=480, altura=270)
                tl = timeline.montar(ep)
                self.assertGreater(tl["total"], 0)
                tl["eventos"] = tl["eventos"][:2]
                tl["total"] = tl["eventos"][-1]["fim"]
                ep.config["video"].update({"largura": 480, "altura": 270, "fps": 12,
                                           "preset": "ultrafast", "crf": 30})
                saida = render.renderizar(ep, tl, preview=True)
                self.assertTrue(saida.exists())
                self.assertGreater(duracao(saida), 1.0)
            finally:
                for m, valor in originais.items():
                    m.RAIZ = valor


if __name__ == "__main__":
    unittest.main(verbosity=2)
