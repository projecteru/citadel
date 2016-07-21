<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ app.name }
</%def>

<%def name="more_css()">
  .block-span { display: block; }
</%def>

<%block name="main">

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">App
	      <a href="${ url_for('app.app_env', name=app.name) }" class="btn-xs">
	        <span class="fui-arrow-right"></span> Environment Variables
	      </a>
      </h3>
    </%def>
    <h4>${ app.name }</h4>
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Latest Versions
        <a href="#" class="btn-xs"><span class="fui-arrow-right"></span> More</a>
      </h3>
    </%def>
    ${ utils.release_list(releases, app) }
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    ${ utils.container_list(containers) }
  </%utils:panel>

</%block>
