# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


# Escala canônica (Não Utilizou fica de fora da média — legado / desk)
AVALIACAO_PARA_VALOR = {
	"Ótimo": 5,
	"Bom": 4,
	"Regular": 3,
	"Ruim": 2,
	"Não Utilizou": None,
}


class RespostadaPesquisa(Document):
	def validate(self):
		self._validar_modelo_e_unidade()
		self._validar_servicos_e_itens()
		self._mapear_valores()
		self._validar_nps()
		self._calcular_media()
		self._definir_anonimato()
		self._validar_contato()

	def _validar_modelo_e_unidade(self):
		if not self.modelo:
			return

		modelo = frappe.get_cached_doc("Modelo de Pesquisa", self.modelo)
		if not modelo.ativo and self.is_new():
			frappe.throw(_("O modelo {0} está inativo.").format(self.modelo))

		if self.company and not modelo.is_company_aplicavel(self.company):
			frappe.throw(
				_(
					"A unidade <b>{0}</b> não está na lista de unidades aplicáveis do modelo <b>{1}</b>."
				).format(self.company, self.modelo),
				title=_("Unidade não aplicável"),
			)

		self.tipo_pesquisa = modelo.tipo_pesquisa
		if not self.texto_nps:
			self.texto_nps = modelo.texto_nps

	def _secoes_do_modelo(self) -> dict[str, int]:
		"""secao -> ordem_secao (apenas perguntas tipo Escala)."""
		modelo = frappe.get_cached_doc("Modelo de Pesquisa", self.modelo)
		mapa: dict[str, int] = {}
		for p in modelo.perguntas or []:
			if p.tipo != "Escala":
				continue
			secao = (p.secao or "").strip()
			if not secao:
				continue
			ordem = cint(p.ordem_secao) or 999
			if secao not in mapa or ordem < mapa[secao]:
				mapa[secao] = ordem
		return mapa

	def _criterios_por_secao(self) -> dict[str, set[str]]:
		modelo = frappe.get_cached_doc("Modelo de Pesquisa", self.modelo)
		out: dict[str, set[str]] = {}
		for p in modelo.perguntas or []:
			if p.tipo != "Escala":
				continue
			secao = (p.secao or "").strip()
			criterio = (p.criterio or "").strip()
			if not secao or not criterio:
				continue
			out.setdefault(secao, set()).add(criterio)
		return out

	def _validar_servicos_e_itens(self):
		if not self.modelo:
			return

		secoes_modelo = self._secoes_do_modelo()
		servicos = []
		seen = set()
		for row in self.servicos_utilizados or []:
			nome = (row.servico or "").strip()
			if not nome:
				continue
			if nome not in secoes_modelo:
				frappe.throw(
					_("Serviço inválido para este modelo: {0}").format(nome),
					title=_("Serviço"),
				)
			if nome in seen:
				continue
			seen.add(nome)
			row.servico = nome
			if not row.ordem:
				row.ordem = secoes_modelo.get(nome) or 0
			servicos.append(nome)

		if not servicos:
			frappe.throw(
				_("Selecione ao menos um serviço utilizado."),
				title=_("Serviços"),
			)

		criterios_ok = self._criterios_por_secao()
		esperados: set[tuple[str, str]] = set()
		for s in servicos:
			for c in criterios_ok.get(s, set()):
				esperados.add((s, c))

		vistos: set[tuple[str, str]] = set()
		for row in self.itens or []:
			secao = (row.secao or "").strip()
			criterio = (row.criterio or "").strip()
			if secao not in seen:
				frappe.throw(
					_(
						"O item <b>{0} / {1}</b> não pertence aos serviços selecionados."
					).format(secao, criterio)
				)
			if (secao, criterio) not in esperados:
				frappe.throw(
					_("Critério inválido: {0} / {1}").format(secao, criterio)
				)
			if not row.avaliacao:
				frappe.throw(
					_("Informe a avaliação de: {0} — {1}").format(secao, criterio)
				)
			vistos.add((secao, criterio))

		faltando = esperados - vistos
		if faltando:
			# lista curta
			amostra = ", ".join(f"{s} / {c}" for s, c in sorted(faltando)[:5])
			extra = f" (+{len(faltando) - 5})" if len(faltando) > 5 else ""
			frappe.throw(
				_("Faltam avaliações para os serviços selecionados: {0}{1}").format(
					amostra, extra
				)
			)

	def _mapear_valores(self):
		for row in self.itens or []:
			if not row.avaliacao:
				row.valor_numerico = None
				continue
			if row.avaliacao not in AVALIACAO_PARA_VALOR:
				frappe.throw(
					_("Avaliação inválida na linha {0}: {1}").format(row.idx, row.avaliacao)
				)
			valor = AVALIACAO_PARA_VALOR[row.avaliacao]
			row.valor_numerico = valor if valor is not None else None

	def _validar_nps(self):
		if self.nps is None or self.nps == "":
			return
		nps = cint(self.nps)
		if nps < 0 or nps > 10:
			frappe.throw(_("O NPS deve ser um número inteiro entre 0 e 10."))
		self.nps = nps

	def _calcular_media(self):
		valores = [
			cint(row.valor_numerico)
			for row in (self.itens or [])
			if row.avaliacao and row.avaliacao != "Não Utilizou" and row.valor_numerico is not None
		]
		if valores:
			self.media_geral = flt(sum(valores) / len(valores), 2)
		else:
			self.media_geral = 0

	def _definir_anonimato(self):
		tem_contato = bool(self.deseja_contato) or bool(self.nome_contato) or bool(self.telefone)
		self.e_anonimo = 0 if tem_contato else 1

	def _validar_contato(self):
		if self.deseja_contato:
			if not self.nome_contato:
				frappe.throw(_("Informe o nome para retorno de contato."))
			if not self.telefone:
				frappe.throw(_("Informe o telefone para retorno de contato."))


@frappe.whitelist()
def carregar_estrutura_do_modelo(modelo: str) -> dict:
	"""Seções (serviços) e critérios do modelo para o Desk."""
	if not modelo:
		return {"servicos": [], "itens": []}

	doc = frappe.get_cached_doc("Modelo de Pesquisa", modelo)
	from collections import OrderedDict

	secoes: OrderedDict[str, dict] = OrderedDict()
	for p in doc.perguntas or []:
		if p.tipo != "Escala":
			continue
		key = (p.secao or "").strip() or "Geral"
		if key not in secoes:
			secoes[key] = {
				"servico": key,
				"ordem": cint(p.ordem_secao) or 999,
				"criterios": [],
			}
		secoes[key]["criterios"].append(p.criterio)

	servicos = list(secoes.values())
	servicos.sort(key=lambda s: (s["ordem"], s["servico"]))
	return {"servicos": servicos}


@frappe.whitelist()
def carregar_itens_do_modelo(modelo: str, servicos: str | list | None = None) -> list[dict]:
	"""Retorna critérios de escala; se servicos informado, filtra por seção."""
	if not modelo:
		return []

	if isinstance(servicos, str):
		import json

		try:
			servicos = json.loads(servicos) if servicos else None
		except json.JSONDecodeError:
			servicos = [s.strip() for s in servicos.split(",") if s.strip()]

	filtro = set(servicos) if servicos else None

	doc = frappe.get_cached_doc("Modelo de Pesquisa", modelo)
	itens = []
	for p in doc.perguntas or []:
		if p.tipo != "Escala":
			continue
		secao = (p.secao or "").strip()
		if filtro is not None and secao not in filtro:
			continue
		itens.append(
			{
				"secao": secao,
				"ordem_secao": p.ordem_secao,
				"criterio": p.criterio,
				"avaliacao": "",
				"valor_numerico": None,
			}
		)
	return itens
