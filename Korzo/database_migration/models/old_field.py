from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    old_id = fields.Integer(string="Old ID")


class HREmployee(models.Model):
    _inherit = "hr.employee"

    old_id = fields.Integer(string="Old ID")


class ResUsers(models.Model):
    _inherit = "res.users"

    old_id = fields.Integer(string="Old ID")


class ResPartner(models.Model):
    _inherit = "res.partner"

    old_id = fields.Integer(string="Old ID")


class UOMCategory(models.Model):
    _inherit = "uom.category"

    old_id = fields.Integer(string="Old ID")


class UOMUOM(models.Model):
    _inherit = "uom.uom"

    old_id = fields.Integer(string="Old ID")


class ProducCategory(models.Model):
    _inherit = "product.category"

    old_id = fields.Integer(string="Old ID")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    old_id = fields.Integer(string="Old ID")


class ProductVariant(models.Model):
    _inherit = "product.product"

    old_id = fields.Integer(string="Old ID")


class Accountpaymentterm(models.Model):
    _inherit = "account.payment.term"

    old_id = fields.Integer(string="Old ID")


class Accountpaymenttermline(models.Model):
    _inherit = "account.payment.term.line"

    old_id = fields.Integer(string="Old ID")


class AccountIncoterms(models.Model):
    _inherit = "account.incoterms"

    old_id = fields.Integer(string="Old ID")


class AccountReconcile(models.Model):
    _inherit = "account.reconcile.model"

    old_id = fields.Integer(string="Old ID")


class Accountaccount(models.Model):
    _inherit = "account.account"

    old_id = fields.Integer(string="Old ID")


class Rescurrency(models.Model):
    _inherit = "res.currency"

    old_id = fields.Integer(string="Old ID")


class Accounttax(models.Model):
    _inherit = "account.tax"

    old_id = fields.Integer(string="Old ID")


class Accounttaxgroup(models.Model):
    _inherit = "account.tax.group"

    old_id = fields.Integer(string="Old ID")


class Rescountry(models.Model):
    _inherit = "res.country"

    old_id = fields.Integer(string="Old ID")


class AccountJournal(models.Model):
    _inherit = "account.journal"

    old_id = fields.Integer(string="Old ID")


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    old_id = fields.Integer(string="Old ID")


class Accountmove(models.Model):
    _inherit = "account.move"

    old_id = fields.Integer(string="Old ID")


class Accountmoveline(models.Model):
    _inherit = "account.move.line"

    old_id = fields.Integer(string="Old ID")


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    old_id = fields.Integer(string="Old ID")


class UTMCampaign(models.Model):
    _inherit = "utm.campaign"

    old_id = fields.Integer(string="Old ID")


class UTMmedium(models.Model):
    _inherit = "utm.medium"

    old_id = fields.Integer(string="Old ID")


class UTMsource(models.Model):
    _inherit = "utm.source"

    old_id = fields.Integer(string="Old ID")


class UTMstage(models.Model):
    _inherit = "utm.stage"

    old_id = fields.Integer(string="Old ID")


class CRMTeam(models.Model):
    _inherit = "crm.team"

    old_id = fields.Integer(string="Old ID")


class AccountPayment(models.Model):
    _inherit = "account.payment"

    old_id = fields.Integer(string="Old ID")


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    old_id = fields.Integer(string="Old ID")


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    old_id = fields.Integer(string="Old ID")


class PdcAccountPayment(models.Model):
    _inherit = "pdc.account.payment"

    old_id = fields.Integer(string="Old ID")


class HrExpense(models.Model):
    _inherit = "hr.expense"

    old_id = fields.Integer(string="Old ID")


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    old_id = fields.Integer(string="Old ID")


class HRDepartment(models.Model):
    _inherit = "hr.department"

    old_id = fields.Integer(string="Old ID")


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    old_id = fields.Integer(string="Old ID")


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    old_id = fields.Integer(string="Old ID")


class PaymentToken(models.Model):
    _inherit = "payment.token"

    old_id = fields.Integer(string="Old ID")


class PartnerIndustry(models.Model):
    _inherit = "res.partner.industry"

    old_id = fields.Integer(string="Old ID")


class Country(models.Model):
    _inherit = "res.country"

    old_id = fields.Integer(string="Old ID")


class CountryState(models.Model):
    _inherit = "res.country.state"

    old_id = fields.Integer(string="Old ID")


class PartnerTitle(models.Model):
    _inherit = "res.partner.title"

    old_id = fields.Integer(string="Old ID")


class AccountGroup(models.Model):
    _inherit = "account.group"

    old_id = fields.Integer(string="Old ID")


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    old_id = fields.Integer(string="Old ID")


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    old_id = fields.Integer(string="Old ID")


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

    old_id = fields.Integer(string="Old ID")


class HrDepartureReason(models.Model):
    _inherit = "hr.departure.reason"

    old_id = fields.Integer(string="Old ID")


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    old_id = fields.Integer(string="Old ID")


class MailActivityPlanTemplate(models.Model):
    _inherit = "mail.activity.plan.template"

    old_id = fields.Integer(string="Old ID")


class MailActivityPlan(models.Model):
    _inherit = "mail.activity.plan"

    old_id = fields.Integer(string="Old ID")


class ProductRemoval(models.Model):
    _inherit = "product.removal"

    old_id = fields.Integer(string="Old ID")


class AccountTaxRepartitionLine(models.Model):
    _inherit = "account.tax.repartition.line"

    old_id = fields.Integer(string="Old ID")


class AccountAccountTag(models.Model):
    _inherit = "account.account.tag"

    old_id = fields.Integer(string="Old ID")


class AccountFinancialReport(models.Model):
    _inherit = "account.financial.report"

    old_id = fields.Integer(string="Old ID")


class AccountCashRounding(models.Model):
    _inherit = "account.cash.rounding"

    old_id = fields.Integer(string="Old ID")


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    old_id = fields.Integer(string="Old ID")


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    old_id = fields.Integer(string="Old ID")


class UtmTag(models.Model):
    _inherit = "utm.tag"

    old_id = fields.Integer(string="Old ID")


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    old_id = fields.Integer(string="Old ID")


class AccountFullReconcile(models.Model):
    _inherit = "account.full.reconcile"

    old_id = fields.Integer(string="Old ID")


class AccountAssetCategory(models.Model):
    _inherit = "account.asset.category"

    old_id = fields.Integer(string="Old ID")


class AccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"

    old_id = fields.Integer(string="Old ID")


class AccountAssetDepreciationLine(models.Model):
    _inherit = "account.asset.depreciation.line"

    old_id = fields.Integer(string="Old ID")


class AccountJornalGroup(models.Model):
    _inherit = "account.journal.group"

    old_id = fields.Integer(string="Old ID")
