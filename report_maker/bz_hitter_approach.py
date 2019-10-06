import glob, os
import pandas as pd
import numpy as np
from matplotlib import pyplot as PLT
from matplotlib import cm as CM
from matplotlib import mlab as ML
from jinja2 import Environment, FileSystemLoader
import pdfkit #needs wkhtmltopdf installed and in PATH (brew install if on macos)
from PyPDF2 import PdfFileMerger
pd.options.display.max_columns=150

class hitter_approach(object):
	'''
	Creates matplotlib images, pandas tables and, ultimately, pdf reports describing batter outcomes versus pitch and plate-location.
	MLB Savant data is used with default naming convention --> savant_data.csv
	Batting data must be used (as opposed to pitching data). Need player_name to be batters.
	'''

	player = "Not yet defined"

	def __init__(self):
		self.savant_data = pd.read_csv('savant_data.csv')



	def print_data_head(self):
		print(self.savant_data.head())



	def list_batters_in_df(self):
		print(np.sort(self.savant_data['player_name'].unique()))



	def create_player_df(self,PLAYER_NAME):

		'''
		Create a df for the player requested. Player's name must have first letters capitalized
		You can see which players are in dataset by using list_batters_in_df function.
		'''

		self.player=PLAYER_NAME

		player_df = self.savant_data[self.savant_data['player_name']==PLAYER_NAME]

		player_df['pitch_type_fast'] = np.where(((player_df['pitch_type']=='FC')|
		                                        (player_df['pitch_type']=='FF')|
		                                        (player_df['pitch_type']=='FT')|
		                                        (player_df['pitch_type']=='SI')),1,0)
		
		player_df['pitch_type_offspeed'] = np.where(((player_df['pitch_type']=='CH')|
		                                        (player_df['pitch_type']=='CU')|
		                                        (player_df['pitch_type']=='EP')|
		                                        (player_df['pitch_type']=='FO')|
		                                        (player_df['pitch_type']=='FS')|
		                                        (player_df['pitch_type']=='SC')|
		                                        (player_df['pitch_type']=='SL')),1,0)
		
		player_df['swing'] = np.where(((player_df['description']!='ball')&
		                              (player_df['description']!='blocked_ball')&
		                              (player_df['description']!='called_strike')),1,0)
		
		player_df['hit'] = np.where(((player_df['events']=='single')|
		                            (player_df['events']=='double')|
		                            (player_df['events']=='triple')|
		                            (player_df['events']=='home_run')),1,0)
		
		player_df['out'] = np.where(((player_df['events']=='double_play')|
		                            (player_df['events']=='field_out')|
		                            (player_df['events']=='fielders_choice')|
		                            (player_df['events']=='fielders_choice_out')|
		                            (player_df['events']=='force_out')|
		                            (player_df['events']=='grounded_into_double_play')|
		                            (player_df['events']=='sac_fly')| #INCLUDE?
		                            (player_df['events']=='strikeout')|
		                            (player_df['events']=='strikeout_double_play')),1,0)

		self.player_data = player_df



	def build_swing_location_heatmap(self,p_throws,fast_offspeed):
		'''
		We will build a heatmap showing swing propensity versus plate location of pitch.
		Need to have created player_data first.
		p_throws can be 'R' or 'L'
		fast_offspeed can be 'fast' or 'offspeed'
		'''
		fast_offspeed = str(fast_offspeed).lower()

		if fast_offspeed=='fast':
			df_relevant = self.player_data[(self.player_data['pitch_type_fast']==1)&(self.player_data['p_throws']==p_throws)]

		else:
			df_relevant = self.player_data[(self.player_data['pitch_type_offspeed']==1)&(self.player_data['p_throws']==p_throws)]

		##Create dataframes detailing situational hitting

		df_relevant['des'].fillna('null_des',inplace=True)
		df_relevant['des'] = df_relevant['des'].astype(str)
		df_relevant.reset_index(inplace=True)
		df_relevant['des'] = df_relevant['des'].map(lambda x:"grounds" if "reaches on a fielder's" in x else x)
		df_relevant['Groundouts'] = df_relevant['des'].map(lambda x:1 if "grounds" in x else 0)
		df_relevant['Flyouts'] = df_relevant['des'].map(lambda x:1 if "flies" in x else 0)
		df_relevant['Lineouts'] = df_relevant['des'].map(lambda x:1 if "lines" in x else 0)
		df_relevant['Popouts'] = df_relevant['des'].map(lambda x:1 if "pops" in x else 0)

		pitches_thrown = df_relevant.shape[0]
		strikes_thrown = df_relevant[df_relevant['swing']==1].shape[0]
		swings_at_strikes = df_relevant[(df_relevant['swing']==1)&
		                                (df_relevant['plate_x']>=-0.958)&
		                                (df_relevant['plate_x']<=0.958)&
		                                (df_relevant['plate_z']>=1.6)&
		                                (df_relevant['plate_z']<=3.55)].shape[0]
		swings_at_balls = df_relevant[(df_relevant['swing']==1)&
		                                ((df_relevant['plate_x']<-0.958)|
		                                (df_relevant['plate_x']>0.958)|
		                                (df_relevant['plate_z']<1.6)|
		                                (df_relevant['plate_z']>3.55))].shape[0]
		total_hits = df_relevant[df_relevant['hit']==1].shape[0]
		total_outs = df_relevant[df_relevant['out']==1].shape[0]
		implied_batting_average = total_hits/(total_hits+total_outs)
		
		XBH = df_relevant[(df_relevant['events']=="double")|
		                  (df_relevant['events']=="triple")|
		                  (df_relevant['events']=="home_run")].shape[0]
		homeruns = df_relevant[df_relevant['events']=="home_run"].shape[0]
		groundouts = df_relevant[df_relevant['Groundouts']==1].shape[0]
		flyouts = df_relevant[df_relevant['Flyouts']==1].shape[0]
		lineouts = df_relevant[df_relevant['Lineouts']==1].shape[0]
		popouts = df_relevant[df_relevant['Popouts']==1].shape[0]

		##Making table 1 and saving it to directory Batting_summary

		tbl1=[]

		categories_tbl1 =[]
		categories_tbl1.append("Pitches Thrown")
		categories_tbl1.append("Strikes Thrown")
		categories_tbl1.append("Swings at Strikes")
		categories_tbl1.append("Swings at Balls")
		categories_tbl1.append("Total Hits")
		categories_tbl1.append("Total Outs")
		categories_tbl1.append("Implied Batting Average - H/(H+O)")
		
		vals_tbl1 = []
		vals_tbl1.append(pitches_thrown)
		vals_tbl1.append(strikes_thrown)
		vals_tbl1.append(swings_at_strikes)
		vals_tbl1.append(swings_at_balls)
		vals_tbl1.append(total_hits)
		vals_tbl1.append(total_outs)
		vals_tbl1.append(implied_batting_average)
		
		tbl1.append(categories_tbl1)
		tbl1.append(vals_tbl1)
		
		tbl1 = pd.DataFrame(tbl1).T
		tbl1.columns=['Stat','Value']
		tbl1['Value']=tbl1['Value'].astype(str)

		tbl1.to_csv('Batting_summary/summary_'+p_throws+'_'+fast_offspeed+'_tbl1.csv',index=False)


		#Making table 2 and saving it to directory Batting_summary

		tbl2=[]

		categories_tbl2 =[]
		categories_tbl2.append("XBH")
		categories_tbl2.append("Home Run")
		categories_tbl2.append("Flyball Outs")
		categories_tbl2.append("Groundball Outs")
		categories_tbl2.append("Line Outs")
		categories_tbl2.append("Pop Outs")
		
		vals_tbl2 = []
		vals_tbl2.append(XBH)
		vals_tbl2.append(homeruns)
		vals_tbl2.append(flyouts)
		vals_tbl2.append(groundouts)
		vals_tbl2.append(lineouts)
		vals_tbl2.append(popouts)
		
		tbl2.append(categories_tbl2)
		tbl2.append(vals_tbl2)
		
		tbl2 = pd.DataFrame(tbl2).T
		tbl2.columns=['Stat','Value']
		tbl2['Value']=tbl2['Value'].astype(str)

		tbl2.to_csv('Batting_summary/summary_'+p_throws+'_'+fast_offspeed+'_tbl2.csv',index=False)




		##Create swing propensity-location heatmaps

		x = df_relevant['plate_x']
		y = df_relevant['plate_z']
		z = df_relevant['swing']
		X, Y = np.meshgrid(x, y)
		
		gridsize=20
		PLT.figure(figsize=(12,8))
		PLT.subplot(111)
		
		PLT.hexbin(x, y, C=z, gridsize=gridsize, cmap=CM.jet, bins=None)
		PLT.axis([x.min(), x.max(), y.min(), y.max()])
		
		cb = PLT.colorbar()
		cb.set_label('mean value')
		
		PLT.plot([0.958, 0.958], [0, 5], color='green', linestyle='-', linewidth=3)
		PLT.plot([-0.958, -0.958], [0, 5], color='green', linestyle='-', linewidth=3)
		
		PLT.plot([-2, 2], [1.60, 1.60], color='green', linestyle='-', linewidth=3)
		PLT.plot([-2, 2], [3.55, 3.55], color='green', linestyle='-', linewidth=3)

		PLT.plot([0, 0], [1, 4], color='red', linestyle='--', linewidth=3) #red midline
		PLT.plot([-2, 2], [2.575, 2.575], color='red', linestyle='--', linewidth=3) #red midline
		
		PLT.xticks(np.arange(-3, 4, step=1))
		PLT.yticks(np.arange(0, 5, step=1))

		PLT.title('Swing Rate Plotted Against Plate Location', fontsize=16)
		
		PLT.savefig('Batting_heatmaps/swings_'+p_throws+'_'+fast_offspeed+'.png',transparent=False, bbox_inches='tight', pad_inches=0.3)



	def build_batting_breakdown(self,p_throws,fast_offspeed,result):
		'''
		player_nm is case-and-spelling sensitive,
    	result can be 'exit_velo', 'hit' or 'out',
    	p_throws can be 'R' or 'L',
    	fast_offspeed can be 'fast' or 'offspeed'
		'''

		fast_offspeed = str(fast_offspeed).lower()
		result = str(result).lower()

		##Create relevant slice of data

		if result == 'exit_velo':
			if fast_offspeed=='fast':
				df_relevant = self.player_data[(self.player_data['pitch_type_fast']==1)&(self.player_data['p_throws']==p_throws)&(self.player_data['swing']==1)&(self.player_data['launch_speed']!='null')]
			else:
				df_relevant = self.player_data[(self.player_data['pitch_type_offspeed']==1)&(self.player_data['p_throws']==p_throws)&(self.player_data['swing']==1)&(self.player_data['launch_speed']!='null')]

			result = "launch_speed"
            
		else:
			if fast_offspeed=='fast':
				df_relevant = self.player_data[(self.player_data['pitch_type_fast']==1)&(self.player_data['p_throws']==p_throws)&(self.player_data['swing']==1)&(self.player_data['events']!='strikeout')]
			else:
				df_relevant = self.player_data[(self.player_data['pitch_type_offspeed']==1)&(self.player_data['p_throws']==p_throws)&(self.player_data['swing']==1)&(self.player_data['events']!='strikeout')]

    	##Create situational location heatmap

		x = df_relevant['plate_x']
		y = df_relevant['plate_z']
		z = df_relevant[result]
		X, Y = np.meshgrid(x, y)
		
		gridsize=12
		PLT.figure(figsize=(12,8))
		PLT.subplot(111)
		
		PLT.hexbin(x, y, C=z, gridsize=gridsize, cmap=CM.jet, bins=None)
		PLT.axis([x.min(), x.max(), y.min(), y.max()])
		
		cb = PLT.colorbar()
		cb.set_label('mean value')
		
		PLT.plot([0.958, 0.958], [1, 4], color='green', linestyle='-', linewidth=3) #in/off plate
		PLT.plot([-0.958, -0.958], [1, 4], color='green', linestyle='-', linewidth=3)
		
		PLT.plot([-2, 2], [1.60, 1.60], color='green', linestyle='-', linewidth=3) #upper/lower strikezones
		PLT.plot([-2, 2], [3.55, 3.55], color='green', linestyle='-', linewidth=3)
		
		PLT.plot([0, 0], [1, 4], color='red', linestyle='--', linewidth=3) #red midline
		PLT.plot([-2, 2], [2.575, 2.575], color='red', linestyle='--', linewidth=3) #red midline
		
		PLT.xticks(np.arange(-3, 4, step=1))
		PLT.yticks(np.arange(0, 6, step=1))
		if result=='out':
		    PLT.title('Outs Plotted Against Plate Location for All Swings', fontsize=16)
		elif result=='hit':
			PLT.title('Hits Plotted Against Plate Location for All Swings', fontsize=16)
		else:
		    PLT.title('Exit Velocity Plotted Against Plate Location for All Contact', fontsize=16)
		
		PLT.savefig('Batting_heatmaps/batting_'+result+'_'+p_throws+'_'+fast_offspeed+'.png',transparent=False, bbox_inches='tight', pad_inches=0.3)



	def make_all_report_images(self):

		for handedness in ['R','L']:
			for pitch_speed in ['fast','offspeed']:
				self.build_swing_location_heatmap(p_throws=handedness,fast_offspeed=pitch_speed)
				for result in ['exit_velo','hit','out']:
					self.build_batting_breakdown(p_throws=handedness,fast_offspeed=pitch_speed,result=result)



	def create_report(self):

		#Load html template that will be transformed into pdf
		env = Environment(loader=FileSystemLoader('.'))
		template = env.get_template("baseball_report_template.html")

		for handedness in ['R','L']:
			for pitch_speed in ['fast','offspeed']:

				##Load up the tbl1 and tbl2 summary stats
				tbl1 = pd.read_csv('Batting_summary/summary_'+handedness+'_'+pitch_speed+'_tbl1.csv')
				tbl1['Value'] = tbl1['Value'].astype(str)
				tbl1.loc[6]['Value']=tbl1.loc[6]['Value'][0:5]
				for idx in range(0,6):
					tbl1.loc[idx]['Value'] = tbl1.loc[idx]['Value'][:-2]
				tbl2 = pd.read_csv('Batting_summary/summary_'+handedness+'_'+pitch_speed+'_tbl2.csv')

				##Populate the place holders in the html template
				template_vars = {"title" : "Batter Approach Review",
        		         "player_nm": self.player,
        		        "handedness": handedness,
        		        "pitch_type": pitch_speed,
        		        "tbl1":tbl1.to_html(index=False),
        		        "tbl2":tbl2.to_html(index=False),
        		        "swing_incidence": 'Batting_heatmaps/swings_'+handedness+'_'+pitch_speed+'.png',
        		        "exit_velo": 'Batting_heatmaps/batting_launch_speed_'+handedness+'_'+pitch_speed+'.png',
        		        "hit_incidence":'Batting_heatmaps/batting_hit_'+handedness+'_'+pitch_speed+'.png',
        		        "out_incidence":'Batting_heatmaps/batting_out_'+handedness+'_'+pitch_speed+'.png'}
		
				html_out = template.render(template_vars)
		
				# to save the results
				with open("my_new_file.html", "w") as fh:
				    fh.write(html_out)
		
				pdfkit.from_file('my_new_file.html','report_'+handedness+'_'+pitch_speed+'.pdf')

		##Combine each batting_situation pds into a single report
		pdfs = []
		pdfs.append('report_R_fast.pdf')
		pdfs.append('report_R_offspeed.pdf')
		pdfs.append('report_L_fast.pdf')
		pdfs.append('report_L_offspeed.pdf')
		
		merger = PdfFileMerger()


		##Merge then remove intermediary files 
		for pdf in pdfs:
		    merger.append(open(pdf, 'rb'),import_bookmarks=False)
		    os.remove(pdf)  
		    
		with open(self.player.split(' ')[0]+'_'+self.player.split(' ')[1]+"_batting_report.pdf", "wb") as fout:
		    merger.write(fout)
		os.remove('my_new_file.html')


		
		





