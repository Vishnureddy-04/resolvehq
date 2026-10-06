/* ResolveHQ frontend config — the only place the API address lives.
   After deploying the backend on Render, put its URL in PROD_API below. */
(function () {
  var PROD_API = 'https://resolvehq-backend.onrender.com/api';
  var local = /^(localhost|127\.0\.0\.1|0\.0\.0\.0)$/.test(location.hostname) || location.protocol === 'file:';
  window.RESOLVEHQ_API = local ? 'http://localhost:5000/api' : PROD_API;
})();
