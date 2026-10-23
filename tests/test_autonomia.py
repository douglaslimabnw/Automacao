"""Testes da camada autônoma: agente, portões de QC, fila e showrunner."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fabrica import agente, qc, showrunner  # noqa: E402
from fabrica.config import Episodio  # noqa: E402


class TestAgente(unittest.TestCase):
    def test_mock_escreve_o_arquivo_pedido(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = (
                "EPISÓDIO A ESCREVER\nNÚMERO: 7\nTÍTULO: A Última Porta\n"
                "TEMA: o corredor que ninguém atravessou\n"
                "Salve no arquivo `episodes/ep-teste/roteiro.md`."
            )
            r = agente.executar(prompt, provedor="mock", cwd=Path(tmp))
            self.assertTrue(r.ok)
            saida = Path(tmp) / "episodes/ep-teste/roteiro.md"
            self.assertTrue(saida.exists())
            texto = saida.read_text(encoding="utf-8")
            self.assertIn("# Episódio 07", texto)
            self.assertIn("> GANCHO", texto)
            self.assertIn("visual:", texto)

    def test_provedor_desconhecido_falha_alto(self):
        with self.assertRaises(SystemExit):
            agente.executar("x", provedor="inexistente")


class TestQC(unittest.TestCase):
    def test_roteiro_real_aprovado(self):
        ep = Episodio("ep-01-o-reino-que-esqueceu-o-sol")
        rel = qc.avaliar_roteiro(ep, [])
        self.assertTrue(rel.aprovado, rel.texto())
        self.assertGreater(len(rel.itens), 8)

    def test_similaridade_detecta_copia(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.md"
            b = Path(tmp) / "b.md"
            texto = " ".join(["o sino tocou e o reino esqueceu o sol"] * 40)
            a.write_text(texto, encoding="utf-8")
            b.write_text(texto, encoding="utf-8")
            na, nb = qc._ngramas(texto), qc._ngramas(b.read_text(encoding="utf-8"))
            j = len(na & nb) / len(na | nb)
            self.assertGreater(j, 0.9)

    def test_cliche_reprovado(self):
        ep = Episodio("ep-01-o-reino-que-esqueceu-o-sol")
        texto_original = [c.get("narracao", "") for c in ep.cenas]
        try:
            for c in ep.cenas:
                if c.get("narracao"):
                    c["narracao"] = ("Em conclusão, vamos explorar esse cenário "
                                     "fascinante e mergulhe nessa jornada. ") * 4
            rel = qc.avaliar_roteiro(ep, [])
            item = next(i for i in rel.itens if i.nome == "sem clichês de IA")
            self.assertFalse(item.ok)
        finally:
            for c, antes in zip(ep.cenas, texto_original):
                c["narracao"] = antes


class TestFilaEShowrunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self._orig = {showrunner: showrunner.RAIZ}
        showrunner.RAIZ = self.raiz
        (self.raiz / "fila.json").write_text(
            json.dumps({"serie": "teste", "itens": []}), encoding="utf-8")

    def tearDown(self):
        for mod, valor in self._orig.items():
            mod.RAIZ = valor
        self.tmp.cleanup()

    def test_slug(self):
        self.assertEqual(showrunner.slugificar("O Segundo Sino", 3), "ep-03-o-segundo-sino")
        self.assertTrue(showrunner.slugificar("Ação & Reação!", 12).startswith("ep-12-acao-reacao"))

    def test_enfileirar_e_proximo(self):
        showrunner.enfileirar([{"titulo": "Um", "brief": "b1"},
                               {"titulo": "Dois", "brief": "b2"}], serie="teste")
        fila = showrunner.carregar_fila()
        self.assertEqual(len(fila["itens"]), 2)
        self.assertEqual([i["numero"] for i in fila["itens"]], [1, 2])
        proximo = showrunner.proximo_pendente()
        self.assertEqual(proximo["titulo"], "Um")
        showrunner.marcar(proximo, "pronto")
        self.assertEqual(showrunner.proximo_pendente()["titulo"], "Dois")

    def test_nao_duplica_numero(self):
        showrunner.enfileirar([{"numero": 1, "titulo": "Um"}], serie="teste")
        showrunner.enfileirar([{"numero": 1, "titulo": "Outro"}], serie="teste")
        self.assertEqual(len(showrunner.carregar_fila()["itens"]), 1)

    def test_pausar_interrompe(self):
        showrunner.enfileirar([{"titulo": "Um", "brief": "x"}], serie="teste")
        (self.raiz / "PAUSAR").write_text("", encoding="utf-8")
        resumo = showrunner.produzir(serie="teste", sem_render=True, provedor="mock")
        self.assertEqual(resumo["status"], "pausado")

    def test_estado_e_dashboard(self):
        showrunner.enfileirar([{"titulo": "Um"}], serie="teste")
        dados = showrunner.estado_geral()
        self.assertEqual(len(dados["itens"]), 1)
        painel = showrunner.escrever_dashboard()
        self.assertIn("Painel", painel.read_text(encoding="utf-8"))


class TestPrompts(unittest.TestCase):
    def test_todos_os_prompts_existem_e_tem_placeholders(self):
        for nome in ("roteiro", "critica", "ideias"):
            p = RAIZ / "prompts" / f"{nome}.md"
            self.assertTrue(p.exists(), f"prompt ausente: {nome}")
            self.assertIn("{{", p.read_text(encoding="utf-8"))

    def test_montar_prompt_substitui(self):
        texto = showrunner.montar_prompt("roteiro", serie="X", premissa="Y",
                                         publico="Z", biblia="B", anteriores="A",
                                         numero=4, titulo="T", brief="b",
                                         gancho_final="g", tema="t",
                                         caminho_saida="episodes/x/roteiro.md",
                                         palavras_alvo=1900)
        self.assertIn("X", texto)
        self.assertNotIn("{{SERIE}}", texto)
        self.assertNotIn("{{", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
