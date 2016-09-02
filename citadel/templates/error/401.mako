<%inherit file="./error_base.mako"/>

<%def name="error_content()">
  <h1>Need to login</h1>
  <p><a href="${ url_for('user.login') }">Click me to login</a></p>
  <p>This is a 401 page</p>
</%def>
