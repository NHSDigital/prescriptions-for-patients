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
var ctxB64 = Buffer.from(JSON.stringify(ctx)).toString('base64url');
context.setVariable('nhsd.delegation.context_b64', ctxB64);
