// JS policy: DelegationSetHeaders.js
var actorSub = context.getVariable('jwt.claim.sub'); // from VJWT-Actor (overwrites claim vars)
var subjectNhs = context.getVariable('nhsd.subject.nhs_number');
if (actorSub) context.setVariable('nhsd.actor.nhs_number', actorSub);

// Build compact context header
var ctx = {
  delegated_access: true,
  subject: { nhs_number: subjectNhs },
  actor:   { nhs_number: actorSub }
};
// var ctxJson = JSON.stringify(ctx);
// var ctxB64 = org.apache.commons.codec.binary.Base64.encodeBase64URLSafeString(
//   new java.lang.String(ctxJson).getBytes("UTF-8")
// );
// context.setVariable('nhsd.delegation.context_b64', ctxB64);
