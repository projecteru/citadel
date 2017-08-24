<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">User ${ user.name }</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Apps for ${ user.name } / ${ user.real_name }</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Git</th>
          <th>Update</th>
        </tr>
      </thead>
      <tbody>
        % for app in apps:
          <tr>
            <td>${ app.name }</td>
            <td>${ app.git }</td>
            <td>${ app.updated }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

</%block>
