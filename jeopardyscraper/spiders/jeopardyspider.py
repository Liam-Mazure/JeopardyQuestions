import scrapy
import re


class JeopardyspiderSpider(scrapy.Spider):
    name = "jeopardyspider"
    allowed_domains = ["j-archive.com", "www.j-archive.com"]
    start_urls = ["https://www.j-archive.com/listseasons.php"]

    def parse(self, response):
        current_season = response.meta.get("current_season",1)
        current_episode = response.meta.get("current_episode",1)

        print(f"Processing Season {current_season}, Episode {current_episode}")
        print(f"Current URL: {response.url}")

        all_seasons_link = response.css('#navbartext a::attr(href)').getall()[2]
        print(all_seasons_link)
        yield response.follow('https://www.j-archive.com/' + all_seasons_link, callback = self.parse_all_seasons, meta = {'current_season': current_season, "current_episode": current_episode})  


    def parse_jeopardy(self, response):
        #Fetching from parse_episode()
        current_season = response.meta.get("current_season")
        current_episode = response.meta.get("current_episode")

        round_1 = response.css('div #jeopardy_round')
        categories = response.css('div #jeopardy_round .category .category_name::text').getall()
        questions = response.css('div #jeopardy_round td.clue')
    
        question_num = 1
        row_num = 1


        if round_1 and categories:
            for index, question in enumerate(questions):
                assigned_category = categories[index % len(categories)]

                question_text = question.xpath("//*[@id ='clue_J_{}_{}']/text()".format(question_num, row_num)).get()
                question_res = question.css('.correct_response::text').get()

                if question_num >= 6:
                    question_num = 1
                    if row_num >= 5:
                        row_num = 1
                    else:
                        row_num += 1
                else:
                    question_num += 1

                yield{
                    'cur_season': current_season,
                    'cur_episode': current_episode,
                    'category': assigned_category,
                    'question_text': question_text,
                    'question_res': question_res
                }


    def parse_double_jeopardy(self, response):
        current_season = response.meta.get("current_season")
        current_episode = response.meta.get("current_episode")

        round_2 = response.css('div #double_jeopardy_round')
        categories = response.css('div #double_jeopardy_round .category .category_name::text').getall()
        questions = response.css('div #double_jeopardy_round td.clue')

        question_num = 1
        row_num = 1

        if round_2 and categories:
            for index, question in enumerate(questions):
                assigned_category = categories[index % len(categories)]

                question_text = question.xpath("//*[@id ='clue_DJ_{}_{}']/text()".format(question_num, row_num)).get()
                question_res = question.css('.correct_response::text').get()

                if question_num >= 6:
                    question_num = 1
                    if row_num >= 5:
                        row_num = 1
                    else:
                        row_num += 1
                else:
                    question_num += 1

                yield{
                    'cur_season': current_season,
                    'cur_episode': current_episode,
                    'category': assigned_category,
                    'question_text': question_text,
                    'question_res': question_res
                }

    def parse_all_seasons(self,response):

        current_season = response.meta.get("current_season", 1)
        current_episode = response.meta.get("current_episode", 1)
        total_episodes = 0

        if 'listseasons.php' in response.url:
            #Query to find each seasons total number of episodes
            num_episodes_query = response.xpath("//div[@id = 'content']//table//tr[td[1]/a[starts-with(text(), 'Season')]]/td[3]/text()").getall()
            num_episodes_query.reverse()
            print(f"Fetched num episodes list: {num_episodes_query}")
            num_episodes = num_episodes_query[current_season - 1]
            print(f"Raw Num_episodes: {num_episodes}")
        else:
            self.logger.error("Not on all seasons page")

        if num_episodes:
            #Splits string into a list where the 0th element is the episode number 
            num_list = re.search(r'\d+', num_episodes)
            print(f"Regex search result: {num_list}")
            if num_list:
                #int storing the episodes in the current season from the prvious string
                total_episodes = int(num_list.group(0))
                print(f"Total Episodes Found: {total_episodes}")
            else:
                self.logger.error("Issue with Total Episodes")
        else:
            self.logger.error("No episodes found")

        #Query to all seasons links
        xpath_query = "//div[@id = 'content']//table//tr//td[1]//a/@href"
        #Actually find the all links from the seasons page
        season_links = response.xpath(xpath_query).getall()
        print("Season Links Found: ", season_links)


        #filters out the links that are not numerical seasons
        filtered_season_links = [
            link for link in season_links
            #walrus operator allows assignment inside an expression
            if(match := re.search(r"season=(\d+)", link)) and 1 <= int(match.group(1)) <= 41
        ]
        print("Filtered Season Links: ", filtered_season_links)

        #finds the link in the filtered list that matches the current season
        current_season_link = next(
            (link for link in filtered_season_links if re.search(rf"season={current_season}\b", link)),
            None
        )
        print(f"Current Season Link: {current_season_link}")

        if current_season_link:
            #Splices in and follows the the link found above
            yield response.follow('https://www.j-archive.com/' + current_season_link, callback = self.parse_season, meta = {'current_season': current_season, 'current_episode': current_episode, 'total_episodes': total_episodes})
        else:
            self.logger.error(f"Could not find link for Season {current_season}")
            return
    
    def parse_season(self, response):
        current_season = response.meta.get("current_season", 1)
        current_episode = response.meta.get("current_episode", 1)
        total_episodes = response.meta.get("total_episodes", 0)

        print(f"Extracting episodes from Season {current_season} from: {response.url}")

        if "showseason.php" not in response.url:
            self.logger.error(f"Wrong season page: {response.url}")
            return
        
        #finds the links for each episode in the current season, then reverses it to start at 1.
        episode_links = response.xpath("//table//tr[td[1]/a[starts-with(text(), '#')]]/td[1]/a/@href").getall()
        episode_links.reverse()
        print(f"Season: {current_season}, Season{current_season} Episode Links: ", episode_links)

        if not episode_links:
            self.logger.error(f"No episodes found for season {current_season}")
            return
        
        
        yield response.follow('http://www.j-archive.com/' + episode_links[current_episode - 1], callback = self.parse_episode, meta = {'current_season': current_season, 'current_episode': current_episode, 'episode_links': episode_links, 'total_episodes': total_episodes})
            
    def parse_episode(self, response):
        
        current_season = response.meta.get("current_season", 1)
        current_episode = response.meta.get("current_episode", 1)
        episode_links = response.meta.get("episode_links", [])
        total_episodes = response.meta.get("total_episodes", 0)

        if "showgame.php" not in response.url:
            self.logger.error(f"Wrong episode page: {response.url}")
            return
        
        #Collects all Jeopardy round categories, questions, and responses
        yield from self.parse_jeopardy(response)
        
        #Collects all Double Jeopardy round categories, questions, and responses
        yield from self.parse_double_jeopardy(response)

        next_game = response.xpath("//table[@id = 'contestants_table']//tr//td[3]//a/@href").get()

        if next_game is not None:
            if current_episode < total_episodes:
                yield response.follow('https://www.j-archive.com/' + next_game, callback = self.parse_episode, meta = {'current_season': current_season, 'current_episode': current_episode + 1, 'total_episodes': total_episodes}, dont_filter = True)
            else:
                yield response.follow('https://www.j-archive.com/listseasons.php', callback = self.parse_all_seasons, meta = {'current_season': current_season + 1, 'current_episode': 1}, dont_filter = True)
        else:
            if current_episode < total_episodes:
                yield response.follow(f'https://www.j-archive.com/showseason.php?season={current_season}', callback = self.parse_season, meta = {'current_season': current_season, 'current_episode': current_episode + 1, 'total_episodes': total_episodes}, dont_filter = True)
            else:
                yield response.follow('https://www.j-archive.com/listseasons.php', callback = self.parse_all_seasons, meta = {'current_season': current_season + 1, 'current_episode': 1}, dont_filter = True)

