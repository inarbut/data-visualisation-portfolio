library(tidyverse)
library(dplyr)
library(ggplot2)

df <- read.csv("kills_with_cheater_flag.csv") |> as_tibble() |> mutate(
  attacker_steamid = as.character(attacker_steamid),
  attacker_name = as.character(attacker_name),
  victim_steamid = as.character(victim_steamid),
  headshot = as.logical(headshot),
  noscope = as.logical(noscope),
  thrusmoke = as.logical(thrusmoke),
  penetrated = ifelse(penetrated > 0, TRUE, FALSE),
  is_cheater = as.logical(is_cheater),
  demo = demo
)



df <- df |> group_by(attacker_steamid, attacker_name, is_cheater) |> 
  summarise(avg_headshot_ratio = mean(headshot), 
            kill_amnt = n(), 
            hs_amnt = sum(headshot), 
            smoke_rat = mean(thrusmoke),
            penetrated=mean(penetrated),
            ns=mean(noscope)) |> 
  filter(kill_amnt<70) #to filter myself as in all those demos there is always me

df <- df |> arrange(is_cheater)

ggplot(df, aes(x=kill_amnt, y=smoke_rat)) + geom_point(aes(color=is_cheater))+
  scale_color_manual(
    values = c("TRUE" = "red", "FALSE"="lightblue"),
    labels = c("TRUE" = "Cheater", "FALSE"= "Legit")
      )+
  labs(
    x = "Amount of kills",
    y = "Kills through smoke ratio",
    color = "Player Type"
  ) +
  theme_minimal()


ggplot(df, aes(x=kill_amnt, y=avg_headshot_ratio)) + geom_point(aes(color=is_cheater), opacity=0.7)+
  scale_color_manual(
    values = c("TRUE" = "red", "FALSE"="lightblue"),
    labels = c("TRUE" = "Cheater", "FALSE"= "Legit")
  )+
  labs(
    x = "Amount of kills",
    y = "Headshot ratio",
    color = "Player Type"
  ) +
  theme_minimal()




  
  
  