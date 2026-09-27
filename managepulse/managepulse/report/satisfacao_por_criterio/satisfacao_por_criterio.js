// Copyright (c) 2026, Still Pulse and contributors
// For license information, please see license.txt

frappe.query_reports["Satisfacao por Criterio"] = {
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
			label: __("Serviço (seção)"),
			fieldtype: "Data",
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
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) {
			return value;
		}
		if (column.fieldname === "media" && data.media != null) {
			let color = "#6c757d";
			if (data.media >= 4.5) color = "#28a745";
			else if (data.media >= 3.5) color = "#17a2b8";
			else if (data.media >= 2.5) color = "#ffc107";
			else color = "#dc3545";
			value = `<span style="color:${color};font-weight:600">${value}</span>`;
		}
		return value;
	},
	onload: function (report) {
		frappe.call({
			method: "managepulse.api.metrics.listar_servicos",
			callback: function (r) {
				if (!r.message || !r.message.length) return;
				const field = report.get_filter("servico");
				if (!field) return;
				field.df.fieldtype = "Autocomplete";
				field.df.options = r.message;
				field.refresh();
			},
		});
	},
};
