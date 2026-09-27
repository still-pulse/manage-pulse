// Copyright (c) 2026, Still Pulse and contributors
// For license information, please see license.txt

frappe.query_reports["Analise de Satisfacao"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("De"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("Até"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Unidade"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "modelo",
			label: __("Modelo de Pesquisa"),
			fieldtype: "Link",
			options: "Modelo de Pesquisa",
		},
		{
			fieldname: "tipo_pesquisa",
			label: __("Tipo de Pesquisa"),
			fieldtype: "Select",
			options: "\nPronto Atendimento\nObservação\nOutro",
		},
		{
			fieldname: "servico",
			label: __("Serviço"),
			fieldtype: "Autocomplete",
			options: [],
		},
		{
			fieldname: "canal",
			label: __("Canal"),
			fieldtype: "Select",
			options: "\nManual Desk\nPúblico\nTotem",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nRecebida\nEm análise\nEncerrada",
		},
		{
			fieldname: "visao",
			label: __("Visão"),
			fieldtype: "Select",
			options: "Respostas\nPor Unidade\nPor Serviço",
			default: "Respostas",
			reqd: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) {
			return value;
		}

		if (column.fieldname === "nps" || column.fieldname === "nps_medio") {
			const nps = data.nps != null ? data.nps : data.nps_medio;
			if (nps != null && nps !== "") {
				let color = "#6c757d";
				if (nps >= 9) color = "#28a745";
				else if (nps >= 7) color = "#ffc107";
				else color = "#dc3545";
				value = `<span style="color:${color};font-weight:600">${value}</span>`;
			}
		}

		if (column.fieldname === "nps_score" && data.nps_score != null) {
			const score = data.nps_score;
			let color = "#6c757d";
			if (score >= 50) color = "#28a745";
			else if (score >= 0) color = "#ffc107";
			else color = "#dc3545";
			value = `<span style="color:${color};font-weight:600">${value}</span>`;
		}

		return value;
	},
	onload: function (report) {
		// Preenche sugestões de serviço a partir das respostas
		frappe.call({
			method: "managepulse.api.metrics.listar_servicos",
			callback: function (r) {
				if (!r.message || !r.message.length) return;
				const field = report.get_filter("servico");
				if (!field) return;
				field.df.options = r.message.join("\n");
				// Autocomplete via awesomplete: redefine como Data com opções
				field.df.fieldtype = "Autocomplete";
				field.df.options = r.message;
				field.refresh();
			},
		});
	},
};
