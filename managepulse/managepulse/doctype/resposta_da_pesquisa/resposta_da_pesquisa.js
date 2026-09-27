// Copyright (c) 2026, Still Pulse and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resposta da Pesquisa", {
	refresh(frm) {
		frm.set_query("modelo", () => ({
			filters: { ativo: 1 },
		}));
		frm.add_custom_button(__("Montar itens pelos serviços"), () => {
			montar_itens_pelos_servicos(frm);
		});
	},

	modelo(frm) {
		if (!frm.doc.modelo) {
			frm.clear_table("servicos_utilizados");
			frm.clear_table("itens");
			frm.refresh_fields(["servicos_utilizados", "itens"]);
			return;
		}
		// carrega todos os serviços do modelo; usuário remove os não usados
		frappe.call({
			method:
				"managepulse.managepulse.doctype.resposta_da_pesquisa.resposta_da_pesquisa.carregar_estrutura_do_modelo",
			args: { modelo: frm.doc.modelo },
			freeze: true,
			callback(r) {
				frm.clear_table("servicos_utilizados");
				(r.message?.servicos || []).forEach((s) => {
					const row = frm.add_child("servicos_utilizados");
					row.servico = s.servico;
					row.ordem = s.ordem;
				});
				frm.refresh_field("servicos_utilizados");
				montar_itens_pelos_servicos(frm);
			},
		});
	},

	deseja_contato(frm) {
		if (!frm.doc.deseja_contato) {
			frm.set_value("nome_contato", "");
			frm.set_value("telefone", "");
			frm.set_value("nome_acompanhante", "");
		}
	},
});

frappe.ui.form.on("Item da Resposta", {
	avaliacao(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const mapa = {
			Ótimo: 5,
			Bom: 4,
			Regular: 3,
			Ruim: 2,
			"Não Utilizou": null,
		};
		frappe.model.set_value(cdt, cdn, "valor_numerico", mapa[row.avaliacao] ?? null);
	},
});

function montar_itens_pelos_servicos(frm) {
	if (!frm.doc.modelo) {
		frappe.msgprint(__("Selecione o modelo primeiro."));
		return;
	}
	const servicos = (frm.doc.servicos_utilizados || [])
		.map((r) => r.servico)
		.filter(Boolean);
	if (!servicos.length) {
		frm.clear_table("itens");
		frm.refresh_field("itens");
		frappe.msgprint(__("Marque ao menos um serviço utilizado."));
		return;
	}
	frappe.call({
		method:
			"managepulse.managepulse.doctype.resposta_da_pesquisa.resposta_da_pesquisa.carregar_itens_do_modelo",
		args: { modelo: frm.doc.modelo, servicos: servicos },
		freeze: true,
		freeze_message: __("Carregando critérios..."),
		callback(r) {
			// preserva avaliações já preenchidas quando possível
			const prev = {};
			(frm.doc.itens || []).forEach((it) => {
				if (it.secao && it.criterio && it.avaliacao) {
					prev[`${it.secao}||${it.criterio}`] = it.avaliacao;
				}
			});
			frm.clear_table("itens");
			(r.message || []).forEach((item) => {
				const row = frm.add_child("itens");
				Object.assign(row, item);
				const key = `${item.secao}||${item.criterio}`;
				if (prev[key]) {
					row.avaliacao = prev[key];
					const mapa = { Ótimo: 5, Bom: 4, Regular: 3, Ruim: 2 };
					row.valor_numerico = mapa[row.avaliacao] ?? null;
				}
			});
			frm.refresh_field("itens");
		},
	});
}
