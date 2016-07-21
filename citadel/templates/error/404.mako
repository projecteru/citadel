<%inherit file="/base.mako"/>

<%block name="nav">
</%block>

<%block name="main">
  <div class="center">
    <h1>Void</h1>
    <p>This is a 404 page</p>
  </div>
</%block>

<%def name="more_css()">
  div.center { text-align: center; margin-top: 100px; }
  div.center p { text-align: right; }
</%def>
