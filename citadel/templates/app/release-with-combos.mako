<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ release.name } @ ${ release.sha[:7] }
</%def>

<%def name="more_css()">
  .progress-bar {
  -webkit-transition: none !important;
  transition: none !important;
  }
</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Release</h3>
    </%def>
    <h4><a href="${ url_for('app.get_app', name=app.name) }">${ app.name }</a> @ ${ release.short_sha }</h4>
    % if release.image:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Container
      </button>
    % elif g.user.privilege:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Raw Container
      </button>
    % else:
      <button class="btn btn-info pull-right" disabled>
        <span class="fui-plus"></span> Add Container
      </button>
    % endif
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">app.yaml</h3>
    </%def>

    <pre>${ appspecs | n }</pre>
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    <%utils:container_list containers="${ containers }">
    </%utils:container_list>
  </%call>

</%block>

<%def name="more_body()">

  <%call expr="utils.modal('add-container-modal')">

    <%def name="header()">
      <h3 class="modal-title">Add Container</h3>
    </%def>

    <ul class="nav nav-tabs" id="add-container-form">

      <% active_ = {'active': 'active'} %>
      % for mode, combo in combos.items():
        % if combo.allow(g.user.name) or g.user.privilege:
          <li class="${ active_.pop('active', '') }"><a class="btn" data-target="#${ mode }" data-toggle="tab">${ mode }</a></li>
        % else:
          <li class="${ active_.pop('active', '') } disabled"><a class="btn" data-target="#${ mode }">${ mode }</a></li>
        % endif
      % endfor

    </ul>

    <div class="tab-content">
      <% active_ = {'active': 'active'} %>
      % for mode, combo in combos.items():
        <div class="tab-pane ${ active_.pop('active', '') }" id="${ mode }">
          <br>

          <form id="add-container-form" class="form-horizontal" action="">
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Release</label>
              <div class="col-sm-10">
                <input class="form-control" type="text" name="release" value="${release.name} / ${release.short_sha}" data-id="${release.id}" disabled>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Pod</label>
              <div class="col-sm-10">
                <select name="pod" class="form-control" disabled>
                  <option value="${ combo.podname }">${ combo.podname }</option>
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Node</label>
              <div class="col-sm-10">
                <select class="form-control" name="node" disabled>
                  <option value="_random">Let Eru choose for me</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Entrypoint</label>
              <div class="col-sm-10">
                <select class="form-control" name="entrypoint" disabled>
                  <option value="${ combo.entrypoint }">${ combo.entrypoint }</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Env</label>
              <div class="col-sm-10">
                <select class="form-control" name="envname" disabled>
                  <option value="${ combo.envname }">${ combo.envname }</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">几个？</label>
              <div class="col-sm-10">
                <input class="form-control" type="number" name="count" value="${combo.count}">
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">CPU</label>
              <div class="col-sm-10">
                <select class="form-control" name="cpu" disabled>
                  <option value="${ combo.cpu }" type="number">${ combo.cpu }</option>
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Memory</label>
              <div class="col-sm-10">
                <select class="form-control" name="memory" disabled>
                  <option value="${ combo.memory }">${ combo.memory_str }</option>
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Extra Env</label>
              <div class="col-sm-10">
                <input class="form-control" type="text" name="envs" value="${ combo.env_string() }" disabled>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Network</label>
              <div class="col-sm-10">
                % for name, cidr in networks.iteritems():
                  % if name in combo.networks:
                    <label class="checkbox" for="">
                      <input type="checkbox" name="network" value="${ name }" checked disabled>${ name } - ${ cidr }
                    </label>
                  % endif
                % endfor
              </div>
            </div>
            % if g.user.privilege:
              <div class="form-group collapse advance-form-group">
                <label class="col-sm-2 control-label" for="">Raw</label>
                <div class="col-sm-10">
                  <input class="form-control" type="checkbox" name="raw" value="">
                </div>
              </div>
            % endif
          </form>

        </div>
      % endfor
    </div>

    <%def name="footer()">
      <button class="btn btn-warning pull-left" data-toggle="collapse" data-target=".advance-form-group">老子搞点高级的</button>
      <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
      <button class="btn btn-info" id="add-container-button"><span class="fui-plus"></span>Go</button>
    </%def>

  </%call>

  <%call expr="utils.modal('container-progress')">
    <%def name="header()">
      <h3 class="modal-title">Please wait...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <div class="progress">
      <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="100" aria-valuemin="0" aira-valuemax="100">
        <span class="sr-only">Waiting ...</span>
      </div>
    </div>
  </%call>

</%def>

<%def name="bottom_script()">
  <script src="/citadel/static/js/deploy.js" type="text/javascript"></script>
</%def>
