<%inherit file="/base.mako"/>

<%!
  from citadel.models.container import Container
%>

<%def name="title()">
  Application List
</%def>

<%block name="main">

  <div class="col-md-8 col-md-offset-2">
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Online Pods</th>
          <th>Online Versions</th>
        </tr>
      </thead>
      <tbody>
        % for app in apps:
          <tr>
            <td><a href="${ url_for('app.app', name=app.name) }">${ app.name }</a></td>
            <% containers = Container.get_by(appname=app.name, zone=g.zone) %>
            % if containers:
              <td>
                <span class="label label-${ 'danger' if app.has_problematic_container(g.zone) else 'success' }">${ len(containers) } Containers</span>
              </td>
              <td>
                <% pods = set([c.podname for c in containers])%>
                % for p in pods:
                  <span class="label label-info">${ p }</span>
                % endfor
              </td>
              <td>
                <% versions = set([c.sha for c in containers])%>
                % for v in versions:
                  <span class="label label-info">${ v[:7] }</span>
                % endfor
              </td>
            % else:
              <td><span class="label label-warning">Nothing</span></td>
              <td><span class="label label-warning">No pods</span></td>
              <td><span class="label label-warning">No versions</span></td>
            % endif
          </tr>
        % endfor
      </tbody>
    </table>
  </div>

  % if g.user.privilege:
    <div class="col-md-offset-8 col-md-4">
      <a href="${ url_for('app.index') }?all=1" class="btn"><button class="btn btn-sm btn-info">还有啥</button></a>
    </div>
  % endif

</%block>
