# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class ModelodePesquisa(Document):
	def validate(self):
		self._normalizar_slug()
		self._validar_perguntas()
		self._validar_unidades_duplicadas()

	def _normalizar_slug(self):
		slug = cstr(self.slug).strip().lower()
		slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
		slug = re.sub(r"-+", "-", slug).strip("-")
		if not slug:
			frappe.throw(_("Informe um slug válido (letras, números e hífen)."))
		self.slug = slug

	def _validar_perguntas(self):
		if not self.perguntas:
			frappe.throw(_("Inclua ao menos uma pergunta no modelo."))

		for row in self.perguntas:
			if row.tipo == "Escala" and not row.criterio:
				frappe.throw(_("Linha {0}: critério é obrigatório para perguntas de escala.").format(row.idx))

	def _validar_unidades_duplicadas(self):
		seen = set()
		for row in self.unidades_aplicaveis or []:
			if row.company in seen:
				frappe.throw(_("Unidade duplicada no modelo: {0}").format(row.company))
			seen.add(row.company)

	def get_unidades_aplicaveis(self) -> list[str]:
		return [r.company for r in (self.unidades_aplicaveis or []) if r.company]

	def is_company_aplicavel(self, company: str) -> bool:
		"""Se a lista de unidades estiver vazia, qualquer Company é aceita."""
		unidades = self.get_unidades_aplicaveis()
		if not unidades:
			return True
		return company in unidades
