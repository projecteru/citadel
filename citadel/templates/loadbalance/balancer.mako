<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Balancer ${ name }</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">${ name } : Domain And Rules</h3>
    </%def>

    <table class="table">
      <thead>
        <tr>
          <th>Domain</th>
          <th>Update Rule</th>
          <th>Rule</th>
          <th>Remove</th>
        </tr>
      </thead>
      <tbody>
        % for rule in rules:
        <tr>
            <td>${rule.domain}</td>
            <td>
              <a class="btn btn-xs btn-info" href="${ url_for('loadbalance.update_rule', name=name, domain=rule.domain) }", name="update-record">
                Update Rule
            </td>
            <td>
              <a class="btn btn-xs btn-info" href="${ url_for('loadbalance.rule', name=name, domain=rule.domain) }" name="get-record">
                <span></span> Rule
            </td>
            <td>
              <a class="btn btn-xs btn-warning" href="${ url_for('loadbalance.delete_rule', name=name, domain=rule.domain) }" name="delete-record">
                <span class="fui-trash"></span> Remove
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
    <button class="btn btn-info btn-xs"><a href="${ url_for('loadbalance.add_rule', name=name) }"> Add rule </a></button>
  </%call>

  <div class="col-md-8 col-md-offset-2">
    <form class="form-horizontal" action="${ url_for('loadbalance.add_general_rule', name=name) }" method="POST">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">App Name</label>
        <div class="col-sm-10">
          <select id="" class="form-control" name="appname">
            % for app in all_apps:
              <option value="${ app.name }">${ app.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Entrypoint</label>
        <div class="col-sm-10">
          <% entrypoints = all_apps[0].get_online_entrypoints() %>
          <select id="" class="form-control" name="entrypoint">
            % for e in entrypoints:
              <option value="${ e }">${ e }</option>
            % endfor
            <option value="_all">_all</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Podname</label>
        <div class="col-sm-10">
          <% pods = all_apps[0].get_online_pods() %>
          <select id="" class="form-control" name="podname">
            % for p in pods:
              <option value="${ p }">${ p }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Domain</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="domain">
        </div>
      </div>
      <div class="form-group">
        <div class="col-sm-10 col-sm-offset-2">
          <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
        </div>
      </div>
    </form>
  </div>
</%block>

<%def name="bottom_script()">
  <script src="/citadel/static/js/balancer.js" type="text/javascript"></script>
  <script src="/citadel/static/js/add-loadbalance.js" type="text/javascript"></script>
</%def>
