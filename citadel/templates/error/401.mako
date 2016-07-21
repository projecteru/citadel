<%inherit file="/base.mako"/>

<%block name="nav">
</%block>

<%block name="main">
  <div class="center">
    <h1>Need to login</h1>
    <p><a href="${ url_for('user.login') }">Click me to login</a></p>
    <p>This is a 401 page</p>
  </div>
</%block>

<%def name="more_css()">
  div.center { text-align: center; margin-top: 100px; }
  div.center p { text-align: right; }
</%def>
