# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""Seed dos modelos baseados nos formulários em papel da UPA."""

from __future__ import annotations

import frappe

TEXTO_NPS_PADRAO = (
	"Em uma escala de 0 a 10, o quanto você indicaria esta unidade a um amigo ou familiar?"
)

INSTRUCOES_PADRAO = (
	"<p>Sinalize o seu grau de satisfação: <b>Ótimo</b>, <b>Bom</b>, "
	"<b>Regular</b>, <b>Ruim</b> ou <b>Não Utilizou</b>.</p>"
	"<p>Se desejar retorno de suas observações e comentários, preencha os dados de contato.</p>"
)

# (secao, ordem_secao, criterio)
PRONTO_ATENDIMENTO = [
	("Atendimento da Recepção", 1, "Atenção e gentileza"),
	("Atendimento da Recepção", 1, "Espera para atendimento"),
	("Atendimento da Enfermagem (triagem)", 2, "Atenção e gentileza"),
	("Atendimento da Enfermagem (triagem)", 2, "Espera para atendimento"),
	("Atendimento Médico", 3, "Atenção e gentileza"),
	("Atendimento Médico", 3, "Cuidados prestados"),
	("Atendimento Médico", 3, "Espera para atendimento"),
	("Atendimento do Raio X", 4, "Atenção e gentileza"),
	("Atendimento do Raio X", 4, "Espera para atendimento"),
	("Atendimento da Medicação", 5, "Atenção e gentileza"),
	("Atendimento da Medicação", 5, "Espera para atendimento"),
	("Serviço de Limpeza", 6, "Ambientes"),
	("Serviço de Limpeza", 6, "Banheiros"),
	("Serviço de Portaria", 7, "Atenção e gentileza"),
	("Serviço de Portaria", 7, "Orientações recebidas"),
	("Instalações", 8, "Acomodação"),
	("Instalações", 8, "Sinalização"),
]

OBSERVACAO = [
	("Atendimento da Enfermagem", 1, "Atenção e gentileza"),
	("Atendimento da Enfermagem", 1, "Cuidados prestados"),
	("Atendimento Médico", 2, "Atenção e gentileza"),
	("Atendimento Médico", 2, "Cuidados prestados"),
	("Atendimento Médico", 2, "Clareza das informações"),
	("Atendimento - Radiologia", 3, "Atenção e gentileza"),
	("Atendimento - Radiologia", 3, "Cuidados prestados"),
	("Alimentação", 4, "Sabor"),
	("Alimentação", 4, "Temperatura"),
	("Alimentação", 4, "Horário"),
	("Serviço de Rouparia", 5, "Disponível: roupa de cama e toalhas"),
	("Serviço de Rouparia", 5, "Higienização: leito"),
	("Serviço de Limpeza", 6, "Ambientes"),
	("Serviço de Limpeza", 6, "Banheiros"),
	("Serviço de Portaria", 7, "Atenção e gentileza"),
	("Serviço de Portaria", 7, "Orientações recebidas"),
	("Instalações", 8, "Acomodação"),
	("Instalações", 8, "Sinalização"),
]

MODELOS = [
	{
		"titulo": "PESQUISA UPA - PRONTO ATENDIMENTO",
		"slug": "upa-pronto-atendimento",
		"tipo_pesquisa": "Pronto Atendimento",
		"perguntas": PRONTO_ATENDIMENTO,
	},
	{
		"titulo": "PESQUISA UPA - OBSERVAÇÃO",
		"slug": "upa-observacao",
		"tipo_pesquisa": "Observação",
		"perguntas": OBSERVACAO,
	},
]


def ensure_modelos_upa():
	"""Cria os 2 modelos UPA se ainda não existirem. Não sobrescreve edições manuais."""
	for spec in MODELOS:
		if frappe.db.exists("Modelo de Pesquisa", spec["titulo"]):
			continue
		if frappe.db.exists("Modelo de Pesquisa", {"slug": spec["slug"]}):
			continue
		_criar_modelo(spec)


def _criar_modelo(spec: dict):
	doc = frappe.get_doc(
		{
			"doctype": "Modelo de Pesquisa",
			"titulo": spec["titulo"],
			"slug": spec["slug"],
			"tipo_pesquisa": spec["tipo_pesquisa"],
			"ativo": 1,
			"permite_contato": 1,
			"instrucoes": INSTRUCOES_PADRAO,
			"texto_nps": TEXTO_NPS_PADRAO,
			"perguntas": [
				{
					"secao": secao,
					"ordem_secao": ordem,
					"criterio": criterio,
					"tipo": "Escala",
					"obrigatorio": 0,
				}
				for secao, ordem, criterio in spec["perguntas"]
			],
			# unidades_aplicaveis vazio => qualquer Company
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.logger("managepulse").info(f"Modelo seed criado: {doc.name}")
