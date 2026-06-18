
import streamlit as st, pandas as pd, re, requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
APP_NAME='EstateLaunch Agent Desk'; INDUSTRY='Real Estate'; PAIN='Agents need faster listing pages, brochures, appointment tracking, sales status, and revenue reporting.'; KIND='realestate'
st.set_page_config(page_title=APP_NAME, layout="wide")
st.markdown("""<style>.block-container{max-width:1220px;padding-top:1.4rem}[data-testid=stSidebar]{background:#10252b;color:white}.title{font-size:2rem;font-weight:800;color:#17202a}.sub{color:#5d6673;margin-bottom:1rem}.panel{border:1px solid #dfe5ec;border-radius:8px;padding:1rem;background:white;box-shadow:0 1px 3px rgba(0,0,0,.04)}.kpi{border-left:4px solid #1b6f6a;background:#f5f8fa;border-radius:6px;padding:.7rem 1rem}.tag{background:#e7f2f0;color:#164e4a;border-radius:99px;padding:.15rem .45rem;font-size:.78rem;font-weight:700}</style>""", unsafe_allow_html=True)
st.markdown(f'<div class="title">{APP_NAME}</div><div class="sub">{INDUSTRY} SaaS agent for: {PAIN}</div>', unsafe_allow_html=True)
if "rows" not in st.session_state: st.session_state.rows=[]
if "recipes" not in st.session_state: st.session_state.recipes=[]
if "checked" not in st.session_state: st.session_state.checked={}

def generic():
    with st.sidebar:
        st.header("Workspace"); company=st.text_input("Company","Acme Operations"); lens=st.selectbox("AI operating lens",["Revenue","Efficiency","Risk","Customer Experience"])
    c=st.columns(4); df=pd.DataFrame(st.session_state.rows)
    total=float(df.value.sum()) if not df.empty else 0
    c[0].markdown(f'<div class="kpi"><b>Items</b><br><span style="font-size:1.6rem">{len(df)}</span></div>',unsafe_allow_html=True)
    c[1].markdown(f'<div class="kpi"><b>Value</b><br><span style="font-size:1.6rem">${total:,.0f}</span></div>',unsafe_allow_html=True)
    c[2].markdown('<div class="kpi"><b>Workflow</b><br>Agent plan</div>',unsafe_allow_html=True); c[3].markdown('<div class="kpi"><b>Exports</b><br>CSV + report</div>',unsafe_allow_html=True)
    t1,t2,t3=st.tabs(["AI Intake","Command Board","Reports"])
    with t1:
        with st.form("f"):
            title=st.text_input("Case, project, client, or opportunity"); details=st.text_area("Context",height=150); owner=st.text_input("Owner","Ops Lead"); due=st.date_input("Due",date.today()+timedelta(days=14)); value=st.number_input("Value or cost impact",0.0,10000000.0,5000.0,500.0); status=st.selectbox("Status",["Planned","In Progress","Blocked","Review","Done"])
            if st.form_submit_button("Create agent plan") and title:
                pri=3+int(any(w in details.lower() for w in ['urgent','risk','late','blocked','compliance']))+int(value>10000)
                steps="Clarify outcome | Collect evidence | Assign owner | Draft stakeholder update | Review KPI impact"
                st.session_state.rows.append(dict(title=title,owner=owner,due=str(due),value=value,status=status,priority=min(pri,5),details=details,next_steps=steps)); st.success("Agent plan created")
        st.info("Agentic workflow: intake context, score urgency, create next-best actions, assign owners, track outcomes, and export reports.")
    with t2:
        if df.empty: st.warning("Add an item first.")
        else:
            edited=st.data_editor(df,use_container_width=True,hide_index=True,num_rows="dynamic"); st.session_state.rows=edited.to_dict('records')
            for r in st.session_state.rows: st.markdown(f"<span class='tag'>P{r['priority']}</span> <b>{r['title']}</b> - {r['owner']} by {r['due']}",unsafe_allow_html=True); st.caption(r['next_steps'])
    with t3:
        df=pd.DataFrame(st.session_state.rows)
        if not df.empty:
            st.bar_chart(df.groupby('status')['value'].sum()); report=f"# {APP_NAME} Report\nCompany: {company}\nLens: {lens}\nItems: {len(df)}\nValue: ${df.value.sum():,.0f}\n"
            st.download_button("Download report",report,file_name="agent_report.md"); st.download_button("Download CSV",df.to_csv(index=False),file_name="workflow_board.csv")

def nutrition():
    CAL=dict(chicken=165,beef=250,rice=130,pasta=160,egg=78,milk=42,cheese=400,oil=884,tomato=18,potato=77,onion=40,beans=132,salmon=208,avocado=160,banana=89,oats=389)
    def scrape(url):
        soup=BeautifulSoup(requests.get(url,timeout=8,headers={'User-Agent':'NutriCart/1.0'}).text,'html.parser'); title=(soup.find(['h1','title']) or {}).get_text(strip=True) if soup.find(['h1','title']) else url; lines=[]
        for tag in soup.find_all(['li','p']):
            txt=' '.join(tag.get_text(' ').split())
            if any(w in txt.lower() for w in ['cup','tbsp','tsp','gram','ounce','egg','oil','salt']): lines.append(txt)
        return title,'\n'.join(lines[:40])
    l,r=st.columns([.42,.58])
    with l:
        url=st.text_input('Recipe URL')
        if st.button('Scrape recipe URL') and url:
            try: st.session_state.tmp_title,st.session_state.tmp_ing=scrape(url); st.success('Scraped. Review and save.')
            except Exception as e: st.error(f'Scrape failed; paste manually. {e}')
        with st.form('recipe'):
            name=st.text_input('Recipe name',st.session_state.get('tmp_title','Weeknight Power Bowl')); servings=st.number_input('Servings',1,20,4); ing=st.text_area('Ingredients',st.session_state.get('tmp_ing','2 cups rice\n1 lb chicken\n1 avocado\n2 tomatoes\n1 tbsp oil'),height=190); notes=st.text_area('Prep notes','Batch cook and store portions.'); save=st.form_submit_button('Save recipe')
        if save:
            total=sum(v for k,v in CAL.items() if k in ing.lower()); st.session_state.recipes.append(dict(name=name,servings=servings,ingredients=ing,notes=notes,calories=int(total/max(servings,1)))); st.success('Saved recipe and nutrition estimate.')
    with r:
        for i,rec in enumerate(st.session_state.recipes):
            with st.expander(f"{rec['name']} - {rec['calories']} cal/serving",expanded=True):
                rows=[]
                for line in [x.strip() for x in rec['ingredients'].splitlines() if x.strip()]:
                    key=f'{i}:{line}'; bought=st.checkbox(line,key=key,value=st.session_state.checked.get(key,False)); st.session_state.checked[key]=bought; rows.append({'ingredient':line,'purchased':bought})
                st.progress(sum(x['purchased'] for x in rows)/max(len(rows),1)); st.download_button('Download shopping list',pd.DataFrame(rows).to_csv(index=False),file_name='shopping_list.csv')
        st.caption('Nutrition is a basic planning estimate, not medical advice.')

def trello():
    with st.form('task'):
        a,b,c=st.columns(3); project=a.text_input('Project','Client Portal Relaunch'); task=b.text_input('Work item','Design approval'); owner=c.text_input('Assigned to','Maya'); start=a.date_input('Start',date.today()); end=b.date_input('End',date.today()+timedelta(days=14)); budget=c.number_input('Budget',0.0,999999.0,2500.0,250.0); status=st.selectbox('Status',['Backlog','In Progress','Blocked','Review','Done']); update=st.text_area('Progress update','Waiting on stakeholder feedback.');
        if st.form_submit_button('Add item'): st.session_state.rows.append(dict(project=project,task=task,assignee=owner,start=str(start),end=str(end),budget=budget,status=status,update=update))
    df=pd.DataFrame(st.session_state.rows); st.metric('Budget used',f"${df.budget.sum():,.0f}" if not df.empty else '$0')
    tabs=st.tabs(['Kanban','Timeline','Budget','Reports'])
    with tabs[0]:
        cols=st.columns(5)
        for col,s in zip(cols,['Backlog','In Progress','Blocked','Review','Done']):
            col.subheader(s)
            if not df.empty:
                for _,r in df[df.status==s].iterrows(): col.markdown(f"<div class='panel'><b>{r.task}</b><br>{r.project}<br>{r.assignee}<br>${r.budget:,.0f}</div>",unsafe_allow_html=True)
    with tabs[1]: st.dataframe(df,use_container_width=True)
    with tabs[2]:
        if not df.empty: st.bar_chart(df.groupby('project')['budget'].sum())
    with tabs[3]:
        if not df.empty: st.download_button('Download board CSV',df.to_csv(index=False),file_name='flowboard.csv')

def social():
    source=st.text_area('Paste source text','Launch announcement: our new analytics dashboard helps operators spot budget risk early.',height=150); visual=st.file_uploader('Upload visual reference mockup',type=['png','jpg','jpeg']); brand=st.text_input('Brand voice','Clear, confident, helpful'); cta=st.text_input('CTA','Book a demo'); platforms=st.multiselect('Platforms',['LinkedIn','X','Instagram','TikTok','Facebook','Threads'],default=['LinkedIn','Instagram','X']); start=st.date_input('Schedule start',date.today()+timedelta(days=1))
    if st.button('Generate social campaign'):
        st.session_state.rows=[dict(platform=p,copy=f"{p}: {source[:170]}. CTA: {cta}. Voice: {brand}.",date=str(start+timedelta(days=i*2)),status='Draft') for i,p in enumerate(platforms)]; st.session_state.canva=f"Canva/drawing prompt: SaaS campaign visual based on uploaded reference. Bold headline, product mockup center, CTA bottom-right. Message: {source[:220]}"
    if visual: st.image(visual,width=360)
    if st.session_state.rows:
        df=pd.DataFrame(st.session_state.rows); st.data_editor(df,use_container_width=True,hide_index=True); st.text_area('Canva or visual tool prompt',st.session_state.get('canva',''),height=130); st.link_button('Open Canva','https://www.canva.com/'); st.download_button('Download calendar',df.to_csv(index=False),file_name='social_calendar.csv')

def realestate():
    tabs=st.tabs(['Listing Chat','Appointments & Revenue','Brochure'])
    with tabs[0]:
        photo=st.file_uploader('Upload property image',type=['png','jpg','jpeg']); price=st.text_input('Price','$749,000'); loc=st.text_input('Location','Austin, TX'); deadline=st.date_input('Contact by deadline',date.today()+timedelta(days=21)); agent=st.text_input('Agent contact','Angela Lee, 555-0100'); details=st.text_area('Listing details','4 bed, 3 bath, renovated kitchen, large backyard.')
        if st.button('Generate listing package'): st.session_state.rows.append(dict(headline=f'Modern {loc} Home Listed at {price}',price=price,location=loc,deadline=str(deadline),agent=agent,details=details,promo=f'Discover this property in {loc}. {details} Contact {agent} by {deadline}.',status='New',revenue=0.0))
        if photo: st.image(photo,width=460)
        for x in st.session_state.rows: st.markdown(f"<div class='panel'><b>{x['headline']}</b><br>{x['promo']}</div>",unsafe_allow_html=True)
    with tabs[1]:
        with st.form('appt'):
            client=st.text_input('Buyer / client','Jordan Smith'); d=st.date_input('Appointment date',date.today()+timedelta(days=2)); status=st.selectbox('Status',['Scheduled','Shown','Offer','Under Contract','Closed','Lost']); rev=st.number_input('Expected or closed revenue',0.0,999999.0,12000.0,500.0); notes=st.text_area('Sales support notes','Needs financing pre-approval.');
            if st.form_submit_button('Save appointment'): st.session_state.setdefault('appts',[]).append(dict(client=client,date=str(d),status=status,revenue=rev,notes=notes))
        df=pd.DataFrame(st.session_state.get('appts',[]));
        if not df.empty: st.dataframe(df,use_container_width=True); st.bar_chart(df.groupby('status')['revenue'].sum())
    with tabs[2]:
        if st.session_state.rows:
            x=st.session_state.rows[-1]; brochure=f"# {x['headline']}\nPRICE: {x['price']}\nLOCATION: {x['location']}\nCONTACT DEADLINE: {x['deadline']}\nAGENT: {x['agent']}\n\n{x['details']}\n\nFixed placement: hero image top, price badge upper right, location under title, contact footer."
            st.markdown(brochure); st.download_button('Download brochure',brochure,file_name='property_brochure.md')

{'nutrition':nutrition,'trello':trello,'social':social,'realestate':realestate}.get(KIND,generic)()
