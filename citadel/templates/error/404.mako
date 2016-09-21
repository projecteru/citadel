<%inherit file="./error_base.mako"/>

<%def name="error_content()">
  <h1>${ err.description }</h1>
  <p>This is a 404 page</p>
</%def>
