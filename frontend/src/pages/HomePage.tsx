import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

export function HomePage() {
  const [splashState, setSplashState] = useState<'visible' | 'hiding' | 'hidden'>('visible');

  useEffect(() => {
    /* Mouse glow */
    const mg = document.getElementById('mg');
    const handleMouseMove = (e: MouseEvent) => {
      if (mg) {
        mg.style.left = e.clientX + 'px';
        mg.style.top = e.clientY + 'px';
      }
    };
    document.addEventListener('mousemove', handleMouseMove);

    /* Scroll reveal */
    const ro = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('v');
            ro.unobserve(e.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -50px 0px' }
    );
    document.querySelectorAll('.rev').forEach((el) => ro.observe(el));

    /* Button conic ring spin */
    const buttonCleanups: (() => void)[] = [];
    document.querySelectorAll('.btn').forEach((btn) => {
      let a = 0,
        on = false,
        raf: number | null = null;
      const htmlBtn = btn as HTMLElement;
      
      const onEnter = () => {
        on = true;
        (function s() {
          a += 1.2;
          htmlBtn.style.setProperty('--ba', a + 'deg');
          htmlBtn.style.setProperty('--gba', a + 'deg');
          if (on) raf = requestAnimationFrame(s);
        })();
      };
      
      const onLeave = () => {
        on = false;
        if (raf) cancelAnimationFrame(raf);
      };

      btn.addEventListener('mouseenter', onEnter);
      btn.addEventListener('mouseleave', onLeave);
      
      buttonCleanups.push(() => {
        btn.removeEventListener('mouseenter', onEnter);
        btn.removeEventListener('mouseleave', onLeave);
      });
    });

    /* Nav CTA glow ring */
    const ncta = document.querySelector('.ncta') as HTMLElement;
    let nctaCleanup = () => {};
    if (ncta) {
      let a = 0,
        on = false,
        raf: number | null = null;
      
      const onEnter = () => {
        on = true;
        (function s() {
          a += 1.5;
          ncta.style.setProperty('--na', a + 'deg');
          if (on) raf = requestAnimationFrame(s);
        })();
      };
      const onLeave = () => {
        on = false;
        if (raf) cancelAnimationFrame(raf);
      };

      ncta.addEventListener('mouseenter', onEnter);
      ncta.addEventListener('mouseleave', onLeave);

      nctaCleanup = () => {
        ncta.removeEventListener('mouseenter', onEnter);
        ncta.removeEventListener('mouseleave', onLeave);
      }
    }

    /* Word cycle */
    const words = [
      'Optimized',
      'Transformed',
      'Tailored',
      'Elevated',
      'Accelerated',
      'Sharpened',
      'Unleashed',
    ];
    const wcEl = document.getElementById('wc');
    let wcInterval: any;
    if (wcEl) {
      let i = 0;
      wcInterval = setInterval(() => {
        wcEl.classList.remove('in');
        wcEl.classList.add('out');
        setTimeout(() => {
          i = (i + 1) % words.length;
          wcEl.textContent = words[i];
          wcEl.classList.remove('out');
          wcEl.classList.add('in');
        }, 290);
      }, 2600);
    }

    /* Agent accordion */
    const items = document.querySelectorAll('.agent-item');
    function openItem(idx: number) {
      items.forEach((it, i) => it.classList.toggle('active', i === idx));
    }
    const itemClickHandlers: (() => void)[] = [];
    items.forEach((item) => {
      const onClick = () => {
        const wasActive = item.classList.contains('active');
        items.forEach((it) => it.classList.remove('active'));
        if (!wasActive) item.classList.add('active');
      };
      item.addEventListener('click', onClick);
      itemClickHandlers.push(() => item.removeEventListener('click', onClick));
    });

    function onAccordionScroll() {
      const trigger = window.innerHeight * 0.42;
      let closest = 0,
        minDist = Infinity;
      items.forEach((item, i) => {
        const rect = item.getBoundingClientRect();
        const itemCenter = rect.top + rect.height / 2;
        const dist = Math.abs(itemCenter - trigger);
        if (dist < minDist) {
          minDist = dist;
          closest = i;
        }
      });
      openItem(closest);
    }

    const sec = document.getElementById('agents');
    let secObs: IntersectionObserver | null = null;
    if (sec) {
      secObs = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            window.addEventListener('scroll', onAccordionScroll, { passive: true });
          } else {
            window.removeEventListener('scroll', onAccordionScroll);
          }
        },
        { threshold: 0 }
      );
      secObs.observe(sec);
    }
    openItem(0); // open first

    /* Shared WebGL helper */
    function makeGL(canvasId: string, fragSrc: string) {
      const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
      if (!canvas) return null;
      const gl = canvas.getContext('webgl');
      if (!gl) return null;
      const vs = `attribute vec2 p;void main(){gl_Position=vec4(p,0,1);}`;
      function mk(t: number, s: string) {
        const sh = gl!.createShader(t);
        gl!.shaderSource(sh!, s);
        gl!.compileShader(sh!);
        return sh!;
      }
      const pr = gl.createProgram();
      gl.attachShader(pr!, mk(gl.VERTEX_SHADER, vs));
      gl.attachShader(pr!, mk(gl.FRAGMENT_SHADER, fragSrc));
      gl.linkProgram(pr!);
      gl.useProgram(pr!);
      const b = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, b);
      gl.bufferData(
        gl.ARRAY_BUFFER,
        new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
        gl.STATIC_DRAW
      );
      const loc = gl.getAttribLocation(pr!, 'p');
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      const uRes = gl.getUniformLocation(pr!, 'res');
      const uTime = gl.getUniformLocation(pr!, 't');
      function rs() {
        if (!canvas || !gl) return;
        const w = window.innerWidth;
        const h = window.innerHeight;
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
      window.addEventListener('resize', rs);
      return { gl, uRes, uTime, rs, canvas, cleanup: () => window.removeEventListener('resize', rs) };
    }

    /* SPLASH SHADER */
    const splashRenderer = makeGL(
      'sc',
      `
        precision highp float;
        uniform vec2 res;uniform float t;
        void main(){
          vec2 uv=(gl_FragCoord.xy*2.-res)/min(res.x,res.y);
          float lw=.0018,tt=t*.048;
          vec3 bg=vec3(.024,.024,.059);
          vec3 c1=vec3(.388,.400,.945),c2=vec3(.545,.361,.965),c3=vec3(.024,.714,.831),c4=vec3(.063,.725,.506);
          vec3 col=bg;float ch0=0.,ch1=0.,ch2=0.,ch3=0.;
          for(int i=0;i<5;i++){float fi=float(i);
            ch0+=lw*fi*fi/abs(fract(tt+fi*.014)*5.-length(uv)+mod(uv.x+uv.y,.2));
            ch1+=lw*fi*fi/abs(fract(tt-.011+fi*.014)*5.-length(uv)+mod(uv.x+uv.y,.2));
            ch2+=lw*fi*fi/abs(fract(tt-.022+fi*.014)*5.-length(uv)+mod(uv.x+uv.y,.2));
            ch3+=lw*fi*fi/abs(fract(tt-.033+fi*.014)*5.-length(uv)+mod(uv.x+uv.y,.2));
          }
          col+=c1*clamp(ch0,0.,1.4);col+=c2*clamp(ch1,0.,1.1);col+=c3*clamp(ch2,0.,.9);col+=c4*clamp(ch3,0.,.6);
          gl_FragColor=vec4(clamp(col,0.,1.),1.);
        }
      `
    );

    let splashRaf: number;
    let splashT0: number | null = null;
    if (splashRenderer) {
      splashRenderer.rs();
      function drawSplash(ts: number) {
        if (!splashT0) splashT0 = ts;
        splashRenderer!.gl.uniform2f(
          splashRenderer!.uRes,
          splashRenderer!.canvas.width,
          splashRenderer!.canvas.height
        );
        splashRenderer!.gl.uniform1f(splashRenderer!.uTime, (ts - splashT0) / 1000);
        splashRenderer!.gl.drawArrays(splashRenderer!.gl.TRIANGLE_STRIP, 0, 4);
        splashRaf = requestAnimationFrame(drawSplash);
      }
      splashRaf = requestAnimationFrame(drawSplash);

      setTimeout(() => {
        setSplashState('hiding');
        setTimeout(() => {
          cancelAnimationFrame(splashRaf);
          setSplashState('hidden');
        }, 1000);
      }, 2500);
    } else {
      setSplashState('hidden');
    }

    /* HERO PLASMA SHADER */
    const heroRenderer = makeGL(
      'hc',
      `
        precision highp float;
        uniform vec2 res;uniform float t;
        const float gsw=.015,sc=5.,ls=.2,la=1.,lf=.2,ws=.04,wf=.5,wa=1.,of=.5,os=.266,mnO=.6,mxO=2.,mnW=.01,mxW=.18;
        const int NL=16;
        #define SM(hw,p,q) smoothstep(hw,0.,abs(p-(q)))
        #define CSM(hw,p,q) smoothstep(hw+gsw,hw,abs(p-(q)))
        #define CI(p,r,c) smoothstep(r+gsw,r,length(c-(p)))
        float rnd(float q){return(cos(q)+cos(q*1.3+1.3)+cos(q*1.4+1.4))/3.;}
        float py(float x,float hf,float o){return rnd(x*lf+t*ls)*hf*la+o;}
        void main(){
          vec2 uv=gl_FragCoord.xy/res,sp=(gl_FragCoord.xy-res*.5)/res.x*2.*sc;
          float hf=1.-(cos(uv.x*6.28)*.5+.5),vf=1.-(cos(uv.y*6.28)*.5+.5);
          sp.y+=rnd(sp.x*wf+t*ws)*wa*(.5+hf);sp.x+=rnd(sp.y*wf+t*ws+2.)*wa*hf;
          vec4 bg=mix(vec4(.03,.03,.10,1.),vec4(.08,.03,.16,1.),uv.x),lines=vec4(0.);
          for(int l=0;l<NL;l++){
            float nli=float(l)/float(NL),op=float(l)+sp.x*of,rv=rnd(op+t*os)*.5+.5;
            float hw=mix(mnW,mxW,rv*hf)*.5,off=rnd(op+t*os*(1.+nli))*mix(mnO,mxO,hf);
            float lp=py(sp.x,hf,off),ln=SM(hw,lp,sp.y)*.5+CSM(hw*.15,lp,sp.y);
            float cx=mod(float(l)+t*ls,25.)-12.;
            ln+=CI(vec2(cx,py(cx,hf,off)),.01,sp)*4.;
            vec4 lc=mix(vec4(.36,.20,.94,1.),vec4(.02,.68,.82,1.),nli);
            lines+=ln*lc*rv;
          }
          vec4 col=bg;col*=vf;col+=lines;col.a=1.;gl_FragColor=col;
        }
      `
    );

    let heroRaf: number;
    let heroT0: number | null = null;
    if (heroRenderer) {
      setTimeout(() => heroRenderer.rs(), 60);
      function drawHero(ts: number) {
        if (!heroT0) heroT0 = ts;
        if (heroRenderer!.canvas.width !== heroRenderer!.canvas.offsetWidth) heroRenderer!.rs();
        heroRenderer!.gl.uniform2f(
          heroRenderer!.uRes,
          heroRenderer!.canvas.width,
          heroRenderer!.canvas.height
        );
        heroRenderer!.gl.uniform1f(heroRenderer!.uTime, (ts - heroT0) / 1000);
        heroRenderer!.gl.drawArrays(heroRenderer!.gl.TRIANGLE_STRIP, 0, 4);
        heroRaf = requestAnimationFrame(drawHero);
      }
      heroRaf = requestAnimationFrame(drawHero);
    }

    /* Cleanup */
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      ro.disconnect();
      buttonCleanups.forEach((c) => c());
      nctaCleanup();
      if (wcInterval) clearInterval(wcInterval);
      
      items.forEach((item, i) => item.removeEventListener('click', itemClickHandlers[i]));
      window.removeEventListener('scroll', onAccordionScroll);
      if (secObs) secObs.disconnect();

      if (splashRenderer) splashRenderer.cleanup();
      if (heroRenderer) heroRenderer.cleanup();
      if (splashRaf) cancelAnimationFrame(splashRaf);
      if (heroRaf) cancelAnimationFrame(heroRaf);
    };
  }, []);

  return (
    <>
      <div id="mg"></div>

      {splashState !== 'hidden' && (
        <div id="splash" className={splashState === 'hiding' ? 'hide' : ''}>
          <canvas id="sc"></canvas>
          <div className="sw">
            <h1>ResumeIntel</h1>
            <p>AI-Powered Resume Optimization</p>
          </div>
        </div>
      )}

      {/* HERO */}
      <section className="hero">
        <div className="hbg"></div>
        <div className="hgrid"></div>
        <canvas id="hc"></canvas>

        <div className="hpill">
          <span className="pd"></span>6-Agent AI Pipeline · Live
        </div>
        <h1>
          Your Resume,<br />
          <span className="gline">
            Ruthlessly <span id="wc">Optimized</span>
          </span>
        </h1>
        <p className="hsub">
          Upload your resume, paste a job description. Six AI agents rewrite, score, and align
          your content to land the interview.
        </p>
        <div className="hact">
          <Link to="/optimize" className="btn bp">
            <div className="gr"></div>
            <div className="br"></div>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
            Optimize My Resume
          </Link>
        </div>
        <div className="sbar">
          <div className="st">
            <div className="sn">6</div>
            <div className="sl">AI Agents</div>
          </div>
          <div className="st">
            <div className="sn">≥0.7</div>
            <div className="sl">Quality Gate</div>
          </div>
          <div className="st">
            <div className="sn">≥0.6</div>
            <div className="sl">Alignment</div>
          </div>
          <div className="st">
            <div className="sn">&lt;60s</div>
            <div className="sl">Processing</div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="hiw-sec rev">
        <div className="lbl">How It Works</div>
        <h2 className="stl">From upload to interview-ready.</h2>
        <p className="ssu">Three steps. Under 60 seconds. No manual editing required.</p>

        <div className="hiw-steps">
          <div className="hiw-step">
            <div className="hiw-wm">1</div>
            <div className="hiw-ico" style={{ background: 'rgba(99,102,241,.1)' }}>
              <svg viewBox="0 0 24 24" stroke="#6366f1">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className="hiw-title">Upload your resume</div>
            <div className="hiw-desc">
              Drop a PDF, DOCX, or paste plain text. Then add the job description you're
              targeting. That's all the input the pipeline needs.
            </div>
          </div>

          <div className="hiw-step">
            <div className="hiw-wm">2</div>
            <div className="hiw-ico" style={{ background: 'rgba(139,92,246,.1)' }}>
              <svg viewBox="0 0 24 24" stroke="#8b5cf6">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div className="hiw-title">6 agents run in sequence</div>
            <div className="hiw-desc">
              Parse → Optimize → Quality Gate → Gap Detect → Align → Interview Prep. Each agent
              clears its gate before the next begins. Fully automated.
            </div>
          </div>

          <div className="hiw-step">
            <div className="hiw-wm">3</div>
            <div className="hiw-ico" style={{ background: 'rgba(6,182,212,.1)' }}>
              <svg viewBox="0 0 24 24" stroke="#06b6d4">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <div className="hiw-title">Get your results</div>
            <div className="hiw-desc">
              Scored bullets, keyword gaps, weakness analysis, and a full interview prep kit —
              all generated and ready to export in under 60 seconds.
            </div>
          </div>
        </div>
      </section>

      {/* AGENT ACCORDION */}
      <section id="agents" className="agent-sec rev">
        <div className="lbl">The Pipeline</div>
        <h2 className="stl">6 agents. One pass. Fully optimized.</h2>
        <p className="ssu">
          Each agent runs in sequence — click to expand and see exactly what it does.
        </p>

        <div className="agent-list">
          <div className="agent-item active" data-agent="0">
            <div className="agent-header">
              <div className="agent-num">01</div>
              <div className="agent-name">Resume Parser</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(99,102,241,.1)',
                  border: '.5px solid rgba(99,102,241,.28)',
                  color: '#6366f1',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <polyline points="4 7 4 4 20 4 20 7" />
                  <line x1="9" y1="20" x2="15" y2="20" />
                  <line x1="12" y1="4" x2="12" y2="20" />
                </svg>
                Parse
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Ingests your resume in any format — PDF, DOCX, or plain text — and segments it
                  into structured sections. Each section is tagged with metadata so downstream
                  agents know exactly where to operate.
                </div>
                <div className="agent-chips">
                  <span className="achip">PDF / DOCX / TXT</span>
                  <span className="achip">Section detection</span>
                  <span className="achip">Metadata tagging</span>
                  <span className="achip">Skills extraction</span>
                </div>
              </div>
            </div>
          </div>

          <div className="agent-item" data-agent="1">
            <div className="agent-header">
              <div className="agent-num">02</div>
              <div className="agent-name">Bullet Optimizer</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(16,185,129,.1)',
                  border: '.5px solid rgba(16,185,129,.28)',
                  color: '#10b981',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                Optimize
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Takes every experience bullet and rewrites it to be action-verb-led and
                  metrics-driven. Passive language is eliminated. Vague claims are replaced with
                  quantifiable impact statements wherever the source material allows.
                </div>
                <div className="agent-chips">
                  <span className="achip">Action verbs</span>
                  <span className="achip">Quantified impact</span>
                  <span className="achip">Filler removal</span>
                  <span className="achip">Concision pass</span>
                </div>
              </div>
            </div>
          </div>

          <div className="agent-item" data-agent="2">
            <div className="agent-header">
              <div className="agent-num">03</div>
              <div className="agent-name">Quality Gate</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(245,158,11,.1)',
                  border: '.5px solid rgba(245,158,11,.28)',
                  color: '#f59e0b',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                Gate ≥ 0.7
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Scores the optimized resume against a quality rubric. If the score falls below
                  0.7, the Bullet Optimizer is triggered again with tighter constraints. This loop
                  continues until the threshold is cleared — the pipeline will not proceed
                  otherwise.
                </div>
                <div className="agent-chips">
                  <span className="achip">Quality score ≥ 0.7</span>
                  <span className="achip">Auto-retry loop</span>
                  <span className="achip">Rubric scoring</span>
                  <span className="achip">Hard gate</span>
                </div>
              </div>
            </div>
          </div>

          <div className="agent-item" data-agent="3">
            <div className="agent-header">
              <div className="agent-num">04</div>
              <div className="agent-name">Gap Detector</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(236,72,153,.1)',
                  border: '.5px solid rgba(236,72,153,.28)',
                  color: '#ec4899',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                Detect
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Compares your resume against the target job description to surface missing
                  credentials, experience gaps, and underrepresented skills. Each gap is
                  explained with suggested remedies — not just flagged.
                </div>
                <div className="agent-chips">
                  <span className="achip">Gap analysis</span>
                  <span className="achip">Missing credentials</span>
                  <span className="achip">Weakness report</span>
                  <span className="achip">Remediation hints</span>
                </div>
              </div>
            </div>
          </div>

          <div className="agent-item" data-agent="4">
            <div className="agent-header">
              <div className="agent-num">05</div>
              <div className="agent-name">JD Alignment Agent</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(6,182,212,.1)',
                  border: '.5px solid rgba(6,182,212,.28)',
                  color: '#06b6d4',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                Gate ≥ 0.6
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Rewrites and reshapes your resume language to mirror the job description's
                  vocabulary. Keyword alignment is scored — if below 0.6, the loop runs again.
                  Matched and missing keywords are both surfaced in the results.
                </div>
                <div className="agent-chips">
                  <span className="achip">Alignment ≥ 0.6</span>
                  <span className="achip">Keyword mapping</span>
                  <span className="achip">JD vocabulary match</span>
                  <span className="achip">ATS optimization</span>
                </div>
              </div>
            </div>
          </div>

          <div className="agent-item" data-agent="5">
            <div className="agent-header">
              <div className="agent-num">06</div>
              <div className="agent-name">Interview Prep Generator</div>
              <div
                className="agent-gate"
                style={{
                  background: 'rgba(139,92,246,.1)',
                  border: '.5px solid rgba(139,92,246,.28)',
                  color: '#8b5cf6',
                }}
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                Prep
              </div>
              <svg
                className="agent-chevron"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
            <div className="agent-body">
              <div className="agent-body-inner">
                <div className="agent-desc">
                  Uses the fully optimized resume to generate likely interview questions in STAR
                  format, structured talking points, and confidence anchors. Tailored to the
                  specific role — not generic advice, but targeted preparation material.
                </div>
                <div className="agent-chips">
                  <span className="achip">STAR Q&amp;A</span>
                  <span className="achip">Talking points</span>
                  <span className="achip">Role-specific</span>
                  <span className="achip">Confidence anchors</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="cta" className="csec rev">
        <div className="cbg"></div>
        <h2>Ready to land the interview?</h2>
        <p>Under 60 seconds from upload to a fully optimized, interview-ready resume.</p>
        <Link
          to="/optimize"
          className="btn bp"
          style={{ fontSize: '1rem', padding: '.95rem 2.5rem', position: 'relative', zIndex: 1 }}
        >
          <div className="gr"></div>
          <div className="br"></div>
          Start Optimizing — Free
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </Link>
      </section>

    </>
  );
}
