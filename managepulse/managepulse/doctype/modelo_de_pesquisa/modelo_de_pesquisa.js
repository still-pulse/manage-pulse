// Copyright (c) 2026, Still Pulse and contributors
// For license information, please see license.txt

frappe.ui.form.on("Modelo de Pesquisa", {
	titulo(frm) {
		if (!frm.doc.slug && frm.doc.titulo) {
			frm.set_value("slug", slugify(frm.doc.titulo));
		}
	},
});

function slugify(text) {
	return (text || "")
		.toString()
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/-+/g, "-")
		.replace(/^-|-$/g, "");
}
