// JS policy: DelegationGate.js
var productOpt = context.getVariable('api.product.attribute.nhsd.delegated_access'); // from GetOAuthV2Info
var proxyOpt   = context.getVariable('delegatedaccess.enabled') || 'false';

var effectiveOptIn = (String(productOpt).toLowerCase() === 'true') && (String(proxyOpt).toLowerCase() === 'true');
context.setVariable('nhsd.delegation.enabled', effectiveOptIn);

var topClaims = context.getVariable('jwt.claims'); // JSON string if VerifyJWT set <OutputClaimVariables/>
var claims = topClaims ? JSON.parse(topClaims) : {};
var hasAct = !!claims.act;

context.setVariable('nhsd.delegation.has_act', hasAct);
if (hasAct && !effectiveOptIn) {
  // Signal fault path
  context.setVariable('nhsd.delegation.reject_reason', 'delegated_access_not_enabled');
  context.setVariable('trigger.raisefault', true);
} else if (hasAct && effectiveOptIn) {
  // Place nested actor token into a variable for VerifyJWT-Actor
  // The structure indicates the actor's ID token is in act.sub
  context.setVariable('jwt.actor.token', claims.act && claims.act.sub);
  // Subject NHS number (patient)
  if (claims.sub) context.setVariable('nhsd.subject.nhs_number', claims.sub);
}
