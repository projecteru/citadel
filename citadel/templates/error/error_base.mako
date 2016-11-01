<%inherit file="/base.mako"/>

<%block name="main">
  <div class="center">
    ${ self.error_content() }
  </div>
</%block>

<%def name="more_css()">
  div.center { text-align: center; margin-top: 100px; }
  div.center p { text-align: right; }
</%def>

<%def name="error_content()">
</%def>
