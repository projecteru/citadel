<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>${ self.title() } · citadel </title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link href="/citadel/static/img/favicon.jpg" rel="shortcut icon">
    <link href="https://staticfile.qnssl.com/flat-ui/2.3.0/css/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet" type="text/css">
    <link href="https://staticfile.qnssl.com/flat-ui/2.3.0/css/flat-ui.min.css" rel="stylesheet" type="text/css">
    <script src="https://staticfile.qnssl.com/flat-ui/2.3.0/js/vendor/jquery.min.js"></script>
    <script src="https://staticfile.qnssl.com/flat-ui/2.3.0/js/flat-ui.min.js"></script>
    <script src="https://cdn.staticfile.org/oboe.js/2.1.2/oboe-browser.min.js"></script>
    <script src="/citadel/static/js/common.js"></script>
    ${ self.more_header() }
    <style>
      ${ self.more_css() }
      nav.navbar {border-radius: 0!important;}
    </style>
  </head>

  <body>

    <%block name="nav">
      <!-- Docs master nav -->
      <nav class="navbar navbar-inverse" role="navigation">
      <div class="navbar-header">
        <a href="${ url_for('app.index') }" class="navbar-brand">citadel</a>
      </div>
      <div class="collapse navbar-collapse">
        <ul class="nav navbar-nav">
          <li class="${ 'active' if request.path.startswith('/app') else '' }">
          <a href="${ url_for('app.index') }"><span class="fui-list-numbered"></span> App List</a>
          </li>
          % if g.user and g.user.privilege:
            <li class="${ 'active' if request.path.startswith('/loadbalance') else '' }">
            <a href="${ url_for('loadbalance.index') }"><span class="fui-windows"></span> Load Balance</a>
            </li>

            <li class="dropdown ${ 'active' if request.path.startswith(url_for('admin.index')) else '' }">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">
              <span class="fui-eye"></span> Admin Area
            </a>
            <ul class="dropdown-menu">
              <li class="${ 'active' if request.path.startswith(url_for('admin.users')) else '' }">
              <a href="${ url_for('admin.users') }"><span class="fui-user"></span> Users</a>
              </li>
              <li class="divider"></li>
              <li class="${ 'active' if request.path.startswith(url_for('admin.pods')) else '' }">
              <a href="${ url_for('admin.pods') }"><span class="fui-list-thumbnailed"></span> Pods</a>
              </li>
              <li class="divider"></li>
              <li class="${ 'active' if request.path.startswith(url_for('admin.oplog')) else '' }">
              <a href="${ url_for('admin.oplog') }"><span class="fui-list-thumbnailed"></span> OPLog</a>
              </li>
            </ul>
            </li>
          % endif
          <li>
          <a href="http://phabricator.ricebook.net/w/develop/platform/deploy-citadel-app/" target="_blank"><span class="fui-question-circle"></span> 我不懂！</a>
          </li>
        </ul>
        <ul class="nav navbar-nav navbar-right">
          <li class="dropdown">
          <a href="#" class="dropdown-toggle" data-toggle="dropdown">${  g.user and g.user.name or u'你谁啊' } <b class="caret"></b></a>
          <ul class="dropdown-menu">
            % if g.user:
              <li><a href="${ url_for('user.logout') }"><span class="fui-power"></span> 再贱</a></li>
            % else:
              <li><a href="${ url_for('user.login') }"><span class="fui-user"></span> 大爷来玩啊</a></li>
            % endif
          </ul>
          </li>
        </ul>
      </div>
      </nav>
    </%block>

    <!-- Docs page layout -->
    <div class="bs-header" id="content">
      <div class="container">
        ${ self.more_content_header() }
      </div>
    </div>

    <div class="container bs-docs-container">
      <div class="row">
        ## TODO support category
        <%
          messages = get_flashed_messages()
        %>
        % if messages:
          <div class="form-group">
            % for m in messages:
              <label class="text-danger">
                <span class="fui-cross-circle"></span> ${ m }
              </label>
            % endfor
          </div>
        % endif
        <%block name="main"></%block>
      </div>
    </div>

    ${ self.more_body() }

    <footer class="footer container">
    ${ self.footer() }
    </footer>

    ${ self.bottom_script() }
  </body>

  <script>
    // enable popover
    $('[rel=popover]').popover();
    // close popover when click outside the popover
    $('body').on('click', function (e) {
    if ($(e.target).data('toggle') !== 'popover' && $(e.target).parents('.popover.in').length === 0) {
      $('[data-toggle="popover"]').popover('hide');
    }
    });
  </script>

</html>

<%def name="more_css()"></%def>
<%def name="more_header()"></%def>
<%def name="title()">Hall</%def>
<%def name="more_body()"></%def>
<%def name="footer()"></%def>
<%def name="bottom_script()"></%def>
<%def name="more_content_header()"></%def>
