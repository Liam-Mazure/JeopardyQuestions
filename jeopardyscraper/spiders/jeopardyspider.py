import scrapy
import re


class JeopardyspiderSpider(scrapy.Spider):
    name = "jeopardyspider"
    allowed_domains = ["www.j-archive.com"]
    start_urls = ["https://www.j-archive.com/showgame.php?game_id=173"]

    def parse(self, response):
        current_season = 1
        current_episode = 1
        # episode_string = response.css('div #game_title h1::text').re(r"#(.)")
        # if episode_string:
        #     episode_num = int(episode_string[0])

        #Either running Jeopary or Double Jeopardy not both. Need to fix!!
        yield from self.parse_jeopardy(response)
        
        yield from self.parse_double_jeopardy(response)

        next_game_links = response.css('#contestants_table tr td a::attr(href)').getall()

        if next_game_links:
            next_game = next_game_links[-1]
            if next_game is not None:
                current_episode += 1
                yield response.follow('https://www.j-archive.com/' + next_game, callback = self.parse)

        else:
            yield from self.parse_no_newpage(response, current_season, current_episode)           


    def parse_jeopardy(self, response):
        round_1 = response.css('div #jeopardy_round')
        categories = response.css('.category')
        questions = response.css('td.clue')
        question_num = 1
        row_num = 1

        if round_1:
            for category_index, category in enumerate(categories):
                    
                category_name = category.css('.category_name::text').get()
                yield{
                    'category' : category_name,
                }
                
            for question in questions:
                question_text = question.xpath("//*[@id ='clue_J_{}_{}']/text()".format(question_num, row_num)).get(),
                question_res = question.css('.correct_response::text').get(),
                
                if question_num >= 6:
                    question_num = 1
                    if row_num >= 5:
                        row_num = 1
                    else:
                        row_num += 1
                else:
                    question_num += 1

                yield{
                    'question_text' : question_text,
                    'question_res' : question_res,
                }

    def parse_double_jeopardy(self, response):
        round_2 = response.css('div #double_jeopardy_round')
        categories = response.css('.category')
        questions = response.css('td.clue')
        question_num = 1
        row_num = 1

        if round_2:
            for category_index, category in enumerate(categories):
                    
                category_name = category.css('.category_name::text').get()
                yield{
                    'category' : category_name,
                }
                
            for question in questions:
                question_text = question.xpath("//*[@id ='clue_DJ_{}_{}']/text()".format(question_num, row_num)).get(),
                question_res = question.xpath("//*[@id ='clue_DJ_{}_{}_r']//*[@class='correct_response']/text()".format(question_num, row_num)).get(),
                
                if question_num >= 6:
                    question_num = 1
                    if row_num >= 5:
                        row_num = 1
                    else:
                        row_num += 1
                else:
                    question_num += 1

                yield{
                    'question_text' : question_text,
                    'question_res' : question_res,
                }

    def parse_no_newpage(self, response, current_season, current_episode):

        all_seasons_link = response.css('#navbartext a::attr(href)').getall()[2]
        response.follow('https://www.j-archive.com/' + all_seasons_link)

        #Query to find the current seasons total number of episodes
        num_episodes_query = "//div[@id = 'content']//table//tr[td[1]/a[text() = 'Season {}']]/td[3]/text()".format(current_season)
        num_episodes = response.xpath(num_episodes_query).get()

        if num_episodes:
            #Splits string into a list where the 2nd element is the episode number 
            num_list = num_episodes.split()
            total_episodes = int(num_list[1])
            

        #Query to find current season link based off of current_season var
        xpath_query = "//div[@id = 'content']//table//tr//td[1]//a[text() = 'Season {}']/@href".format(current_season)
        #Actually find the link from the seasons page
        current_season_link = response.xpath(xpath_query).get()
        #Splices in and follows the the link found above
        yield response.follow('https://www.j-archive.com/' + current_season_link)

        if current_episode >= total_episodes:
            current_season += 1
            yield from self.parse_no_newpage(response, current_season, current_episode)
        else:
            new_page = "//table//tr[{}]/td[1]//a/@href".format(total_episodes-current_episode)
            new_page_link = response.xpath(new_page).get()
            yield response.follow('http://www.j-archive.com/' + new_page_link, callback = self.parse)



